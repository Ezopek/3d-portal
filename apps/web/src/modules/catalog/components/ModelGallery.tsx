import { useState } from "react";

import type { ModelFileRead } from "@/lib/api-types";

function isImage(f: ModelFileRead): boolean {
  return f.kind === "image" || f.kind === "print";
}

function srcFor(modelId: string, fileId: string): string {
  return `/api/models/${modelId}/files/${fileId}/content`;
}

export function ModelGallery({
  modelId,
  files,
}: {
  modelId: string;
  files: readonly ModelFileRead[];
}) {
  const images = files.filter(isImage);
  const [activeId, setActiveId] = useState<string | null>(images[0]?.id ?? null);
  if (images.length === 0) {
    return (
      <div className="grid aspect-[4/3] place-items-center rounded bg-muted text-sm text-muted-foreground">
        no preview
      </div>
    );
  }
  const active = images.find((i) => i.id === activeId) ?? images[0]!;
  return (
    <div className="space-y-2">
      <img
        data-testid="gallery-main"
        src={srcFor(modelId, active.id)}
        alt={active.original_name}
        className="aspect-[4/3] w-full rounded bg-muted object-cover"
      />
      <div className="grid grid-cols-7 gap-1">
        {images.slice(0, 7).map((img) => (
          <button
            key={img.id}
            type="button"
            data-testid="gallery-thumb"
            onClick={() => setActiveId(img.id)}
            className={`aspect-square overflow-hidden rounded ${
              img.id === active.id ? "ring-2 ring-ring" : "opacity-70 hover:opacity-100"
            }`}
          >
            <img
              src={srcFor(modelId, img.id)}
              alt={img.original_name}
              className="h-full w-full object-cover"
            />
          </button>
        ))}
      </div>
    </div>
  );
}
