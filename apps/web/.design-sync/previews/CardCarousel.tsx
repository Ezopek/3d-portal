import { CardCarousel } from "portal-web";

// CardCarousel builds <img> src from /api/models/<id>/files/<id>/content — those
// 404 in the preview environment (no API), so the image area shows the muted
// placeholder; the carousel chrome (prev/next arrows + dot indicators) is the
// component's own UI and renders from the fileIds.
export function Gallery() {
  return (
    <div className="w-64 overflow-hidden rounded-xl ring-1 ring-foreground/10">
      <CardCarousel
        modelId="demo"
        fileIds={["1", "2", "3", "4"]}
        alt="Podgląd modelu"
      />
    </div>
  );
}
