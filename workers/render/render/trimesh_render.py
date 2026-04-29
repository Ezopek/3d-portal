from pathlib import Path

import matplotlib

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


def render_views(*, stl_path: Path, output_dir: Path, size: int = 768) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.load(stl_path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Not a triangle mesh: {stl_path}")

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
