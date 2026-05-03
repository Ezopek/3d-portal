from pathlib import Path

import matplotlib
import trimesh.path.packing as _trimesh_packing

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VIEW_NAMES = ("front", "side", "top", "iso")

# (elev, azim) angles per view name.
_VIEW_ANGLES = {
    "front": (0, -90),
    "side": (0, 0),
    "top": (90, -90),
    "iso": (30, -45),
}


def render_views(*, stl_paths: list[Path], output_dir: Path, size: int = 768) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if len(stl_paths) == 1:
        mesh = trimesh.load(stl_paths[0], force="mesh")
    else:
        mesh = _pack_meshes_xy(stl_paths, spacing_mm=5.0)
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Not a triangle mesh: {stl_paths}")
    return _render_mesh_views(mesh, output_dir, size)


def _pack_meshes_xy(stl_paths: list[Path], spacing_mm: float) -> trimesh.Trimesh:
    placed: list[trimesh.Trimesh] = []
    extents_xy: list[tuple[float, float]] = []
    for path in stl_paths:
        m = trimesh.load(path, force="mesh")
        if not isinstance(m, trimesh.Trimesh):
            continue  # silently skip non-mesh STLs (e.g. multi-geometry Scenes)
        m = m.copy()
        m.apply_translation(-m.bounds[0])  # bbox.min -> origin (bottom on z=0)
        placed.append(m)
        extents_xy.append((float(m.extents[0] + spacing_mm), float(m.extents[1] + spacing_mm)))

    if not placed:
        raise ValueError("no usable triangle meshes for packing")

    # 2D bin-pack: returns (boxes, inserted) where boxes is shape (N, 2, 2)
    # — each entry is [[min_x, min_y], [max_x, max_y]].  The min corner is
    # where we translate each mesh to.
    boxes, _inserted = _trimesh_packing.rectangles(extents_xy)

    for mesh, box in zip(placed, boxes, strict=True):
        tx, ty = float(box[0][0]), float(box[0][1])
        mesh.apply_translation([tx, ty, 0.0])

    return trimesh.util.concatenate(placed)


def _render_mesh_views(mesh: trimesh.Trimesh, output_dir: Path, size: int) -> dict[str, Path]:
    # Normalize: center on origin, scale so longest extent fits.
    mesh = mesh.copy()
    mesh.apply_translation(-mesh.centroid)
    extent = max(mesh.extents)
    if extent > 0:
        mesh.apply_scale(1.0 / extent)

    results: dict[str, Path] = {}
    dpi = 100
    fig_size = size / dpi
    for view, (elev, azim) in _VIEW_ANGLES.items():
        fig = plt.figure(figsize=(fig_size, fig_size), dpi=dpi)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_axis_off()
        ax.set_box_aspect((1, 1, 1))

        polys = mesh.triangles
        collection = Poly3DCollection(
            polys,
            alpha=0.95,
            facecolor="#9ca3af",
            edgecolor="#1f2937",
            linewidth=0.2,
        )
        ax.add_collection3d(collection)
        ax.set_xlim(-0.6, 0.6)
        ax.set_ylim(-0.6, 0.6)
        ax.set_zlim(-0.6, 0.6)
        ax.view_init(elev=elev, azim=azim)
        fig.tight_layout(pad=0)

        out = output_dir / f"{view}.png"
        fig.savefig(out, dpi=dpi, transparent=True)
        plt.close(fig)
        results[view] = out

    return results
