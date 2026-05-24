// Story 22.3 (TB-037 viewer) — lazy barrel mirroring `viewer3d/index.ts`
// shape so consumers (ShareCarousel, ModelGallery) get a code-split chunk
// for the fullscreen image viewer. Importing the default export directly
// from `./ImageFullscreenViewer` would defeat the dynamic import and pull
// the viewer body into the main bundle (per
// `[[feedback_lazy_import_discipline]]`, Story 19.7 precedent).
//
// Consumers must wrap the rendered viewer in `<Suspense fallback={null}>`.

import { lazy } from "react";

export type {
  ImageFullscreenViewerProps,
  ImageRenderer,
  ImageSource,
} from "./types";

export const ImageFullscreenViewer = lazy(
  () => import("./ImageFullscreenViewer"),
);
