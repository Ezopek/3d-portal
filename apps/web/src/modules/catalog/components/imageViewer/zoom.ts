// Story 53.2 (E53 / FR26-VIEW-1) — pure zoom + pan arithmetic for
// `ImageFullscreenViewer`. Kept out of the component on purpose: jsdom has no
// layout engine, so a clamp assertion written against the mounted viewer reads
// all-zero rects and passes trivially. With the geometry injected as plain
// numbers the unit tests in `zoom.test.ts` actually constrain the maths, and
// the component keeps only the measurement + wiring.
//
// Every constant below points at the contract it serves (project-context.md,
// "Magic constants in specs require contract-pointing justification").

/** Fit-to-frame. Story 53.2 D-4: below 1.0 there is nothing to see and Reset
 *  would have two meanings. */
export const MIN_SCALE = 1;

/** Default zoom envelope. D-4 balances `FR26-VIEW-1`'s inspectability goal
 *  against not shipping a blurred upscale as a feature. */
export const BASE_MAX_SCALE = 4;

/** One Zoom In / Zoom Out press, and one `+` / `-` keypress.
 *  `EXPERIENCE.md:282` requires key and button to be the same action. */
export const ZOOM_STEP = 1.5;

/** Double-tap toggles 1.0 <-> this. `EXPERIENCE.md:273` asks for "a fixed
 *  zoom step" whose every reachable state is also reachable by the visible
 *  controls, so the target sits ON the button ladder (two Zoom In presses)
 *  rather than at a value the buttons cannot produce. See D-4's explicit
 *  "snap double-tap to the nearest step boundary" escape. */
export const DOUBLE_TAP_SCALE = ZOOM_STEP * ZOOM_STEP;

export interface Vec2 {
  readonly x: number;
  readonly y: number;
}

export interface Size {
  readonly width: number;
  readonly height: number;
}

function finite(value: number, fallback = 0): number {
  return Number.isFinite(value) ? value : fallback;
}

/** Collapse `-0` to `0` so the emitted `translate()` never reads `-0px`. */
function unsign(value: number): number {
  return value === 0 ? 0 : value;
}

/**
 * Zoom ceiling for the currently rendered image.
 *
 * `ImageSource` carries no pixel dimensions (story V-13), so the ceiling is
 * read from the rendered `<img>`: `naturalWidth` against the CSS width it is
 * laid out at. D-4 — the envelope is {@link BASE_MAX_SCALE}, raised to the
 * native-pixel ratio when the source supports more than that without
 * upsampling past one image-pixel per CSS-pixel (the 4:1 / 8:1 panorama case
 * `epics.md:4579` names). It is never lowered below the default envelope, so
 * a small source still zooms rather than presenting three dead controls.
 *
 * Returns {@link BASE_MAX_SCALE} whenever the geometry is unmeasurable — a
 * pre-decode image, or jsdom, where every layout box is 0.
 */
export function resolveMaxScale(naturalWidth: number, renderedWidth: number): number {
  const natural = finite(naturalWidth);
  const rendered = finite(renderedWidth);
  if (natural <= 0 || rendered <= 0) return BASE_MAX_SCALE;
  return Math.max(BASE_MAX_SCALE, natural / rendered);
}

export function clampScale(scale: number, maxScale: number): number {
  const max = Math.max(MIN_SCALE, finite(maxScale, BASE_MAX_SCALE));
  if (Number.isNaN(scale)) return MIN_SCALE;
  return Math.min(max, Math.max(MIN_SCALE, scale));
}

export function zoomIn(scale: number, maxScale: number): number {
  return clampScale(clampScale(scale, maxScale) * ZOOM_STEP, maxScale);
}

export function zoomOut(scale: number, maxScale: number): number {
  return clampScale(clampScale(scale, maxScale) / ZOOM_STEP, maxScale);
}

/**
 * Target scale for a double-tap. Any zoomed state collapses back to 1.0;
 * 1.0 goes to the fixed step. D-3 — "double-tap toggles between 1.0 and one
 * fixed zoom step".
 */
export function doubleTapTarget(scale: number, maxScale: number): number {
  return scale > MIN_SCALE ? MIN_SCALE : clampScale(DOUBLE_TAP_SCALE, maxScale);
}

/**
 * Clamp a pan offset so no edge of the scaled image can move inside the
 * corresponding frame edge (D-4). `base` is the image's UNSCALED layout box
 * (`offsetWidth`/`offsetHeight`, which the CSS transform does not affect);
 * `frame` is the visible window. At scale 1.0 — or on any axis where the
 * scaled image still fits — the offset is pinned to 0.
 */
export function clampPan(pan: Vec2, scale: number, base: Size, frame: Size): Vec2 {
  const s = Math.max(MIN_SCALE, finite(scale, MIN_SCALE));
  const travelX = Math.max(0, (finite(base.width) * s - finite(frame.width)) / 2);
  const travelY = Math.max(0, (finite(base.height) * s - finite(frame.height)) / 2);
  return {
    x: unsign(Math.min(travelX, Math.max(-travelX, finite(pan.x)))),
    y: unsign(Math.min(travelY, Math.max(-travelY, finite(pan.y)))),
  };
}

/**
 * Re-derive the pan offset so the content point currently under `focus` stays
 * under it while the scale moves `fromScale` -> `toScale`. `focus` is measured
 * from the frame's centre, i.e. the same origin the transform uses.
 *
 * The layer renders as `translate(pan) scale(s)`, so a content point `c` lands
 * at `p = pan + s*c`. Holding `c` fixed gives `pan' = p - (s'/s)*(p - pan)`.
 * This is what makes a pinch scale about the finger midpoint instead of
 * yanking the image back to centre.
 */
export function panForScaleAbout(
  pan: Vec2,
  fromScale: number,
  toScale: number,
  focus: Vec2,
): Vec2 {
  const from = finite(fromScale);
  if (from <= 0) return pan;
  const ratio = finite(toScale) / from;
  return {
    x: focus.x - ratio * (focus.x - finite(pan.x)),
    y: focus.y - ratio * (focus.y - finite(pan.y)),
  };
}
