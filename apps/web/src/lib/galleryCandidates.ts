export interface GalleryImage {
  url: string;
  path: string;
}

export interface PrintLike {
  path: string;
  date: string;
}

export interface ModelLike {
  id: string;
  path: string;
  prints: PrintLike[];
}

const RENDER_VIEWS = ["iso", "front", "side", "top"] as const;

export function pickGalleryCandidates(model: ModelLike, files: string[]): GalleryImage[] {
  const candidates: GalleryImage[] = [];

  for (const f of files) {
    if (f.startsWith("images/") && /\.(png|jpe?g|webp)$/i.test(f)) {
      candidates.push({ url: `/api/files/${model.id}/${f}`, path: f });
    }
  }

  if (model.prints.length > 0) {
    const printsSorted = [...model.prints].sort((a, b) => b.date.localeCompare(a.date));
    for (const p of printsSorted) {
      const segments = p.path.split("/");
      const rel = segments.slice(model.path.split("/").length).join("/");
      if (/\.(png|jpe?g|webp)$/i.test(rel)) {
        candidates.push({ url: `/api/files/${model.id}/${rel}`, path: rel });
      }
    }
  } else {
    for (const f of files) {
      if (f.startsWith("prints/") && /\.(png|jpe?g|webp)$/i.test(f)) {
        candidates.push({ url: `/api/files/${model.id}/${f}`, path: f });
      }
    }
  }

  for (const view of RENDER_VIEWS) {
    candidates.push({
      url: `/api/files/${model.id}/${view}.png`,
      path: `${view}.png`,
    });
  }

  const seen = new Set<string>();
  return candidates.filter((c) => (seen.has(c.path) ? false : seen.add(c.path)));
}
