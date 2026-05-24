// Story 22.3 (TB-037 viewer + TB-022 consumer) — public surface types for the
// symmetric fullscreen image viewer. Kept in a dedicated module so the
// lazy barrel can re-export `ImageFullscreenViewerProps` without forcing the
// barrel itself to eagerly resolve the heavy default export.
//
// Designer §7 — the `renderImage` prop is the cookie-credential boundary.
// On /catalog/<id> consumers pass a plain `<img>` (same-origin cookies
// attach by default — that's the desired behaviour for the authenticated
// surface). On /share/<token> consumers pass the `AnonymousImage` wrapper
// which routes every fetch through `credentials:"omit"` + blob-URL caching
// so the recipient's portal_access cookie never leaks (NFR10/12).
//
// The viewer body trusts its inputs and contains NO auth gate — both mounts
// have already crossed their auth boundary by the time the viewer opens.

import type { ReactElement } from "react";

/**
 * Renderer for a single image inside the viewer (main frame + thumbs both
 * route through this prop). On /catalog/* this is a plain `<img>`; on
 * /share/<token> it's `AnonymousImage` so cookie-omission holds.
 */
export type ImageRenderer = (props: {
  src: string;
  alt: string;
  className?: string;
}) => ReactElement;

/**
 * Source descriptor for one image in the viewer's photo set. `fullUrl` is
 * fetched into the main frame (original-resolution or backend-fallback per
 * Story 22.1 variant routing); `thumbUrl` is fetched into the bottom strip.
 * `alt` is the per-image accessible label.
 */
export interface ImageSource {
  readonly fullUrl: string;
  readonly thumbUrl: string;
  readonly alt: string;
}

/**
 * Props for the `ImageFullscreenViewer` Dialog. The viewer renders the
 * image at `sources[initialIndex]` first, supports prev/next navigation,
 * ESC + Dialog default close, and surfaces mobile gestures
 * (tap-to-toggle-chrome + swipe-LR) per designer §5.
 *
 * Story 22.3 round-2 (Codex P1): the optional `renderThumb` prop lets
 * consumers inject a DIFFERENT renderer for the bottom strip than for
 * the main frame. /share/<token> uses this to pass `LazyAnonymousImage`
 * for the strip (IntersectionObserver-gated) while the main frame stays
 * on plain `AnonymousImage` (always eager — it's the active image).
 * Without this, the viewer's strip on /share/<token> would mount every
 * thumbnail eagerly and bypass the route's existing lazy-strip
 * mitigation (Story 22.2 round-2) — pushing /api/share/* over the 60
 * req/min cap on large galleries.
 *
 * When `renderThumb` is omitted (e.g. /catalog/<id> authenticated
 * mount where no rate-limit applies), it defaults to `renderImage` —
 * preserving the symmetric single-renderer behaviour for the simple
 * case.
 */
export interface ImageFullscreenViewerProps {
  readonly sources: readonly ImageSource[];
  readonly initialIndex: number;
  readonly onClose: () => void;
  readonly renderImage: ImageRenderer;
  readonly renderThumb?: ImageRenderer;
}
