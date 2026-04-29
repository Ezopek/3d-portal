import { useState } from "react";

interface Props { images: string[] }

export function Gallery({ images }: Props) {
  const [active, setActive] = useState(0);
  if (images.length === 0) {
    return (
      <div className="aspect-square w-full rounded-md bg-muted text-center text-sm text-muted-foreground">
        <div className="grid h-full place-items-center">no preview</div>
      </div>
    );
  }
  const safe = images[active] ?? images[0]!;
  return (
    <div>
      <div className="aspect-square w-full overflow-hidden rounded-md bg-muted">
        <img src={safe} alt="" className="h-full w-full object-contain" />
      </div>
      {images.length > 1 && (
        <div className="mt-2 flex gap-2 overflow-x-auto">
          {images.map((src, i) => (
            <button
              key={src}
              type="button"
              onClick={() => setActive(i)}
              className={`size-16 shrink-0 overflow-hidden rounded ${i === active ? "ring-2 ring-ring" : ""}`}
            >
              <img src={src} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
