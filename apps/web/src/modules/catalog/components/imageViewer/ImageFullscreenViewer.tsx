// Story 22.3 (TB-037 viewer + TB-022 consumer) — symmetric fullscreen image
// viewer. ONE component, prop-injected `renderImage`, mounted by both
// `/catalog/$modelId` (ModelGallery) and `/share/$token` (ShareCarousel).
// Designer spec (`22-3-designer-ux-spec.md`) is the binding source of truth
// for every layout / a11y / gesture decision below; this file extracts the
// implementation from that spec.
//
// What lives here:
//   - shadcn Dialog wrapper mirroring `Viewer3DModal` sizing (designer §1+§4)
//   - main image rendered via `renderImage` prop (the cookie-credential
//     boundary; auth tax lives at the prop, not in the viewer body)
//   - bottom thumb strip with active highlight
//   - top-left counter (only when total > 1)
//   - top-right close button + prev/next chevrons
//   - keyboard handler: ESC closes (Dialog default also covers this);
//     ArrowLeft/Right navigates
//   - mobile gestures (designer §5):
//       * tap-to-toggle overlay chrome  — IN-SCOPE
//       * swipe-LR between images       — IN-SCOPE
//       * pinch-to-zoom                 — Story 53.2 (was TB-042)
//       * swipe-down-to-close           — DEFERRED (TB-042 candidate)
//
// NOT included on purpose:
//   - no auth gate (both mounts have crossed their auth boundary already)
//   - no separate /catalog vs /share variants — one component, prop only
//   - no PhotoSwipe / yet-another-react-lightbox dep (boring tech bias per
//     designer §1; the surface is ~150 LOC, we already own focus-trap +
//     theme + i18n via shadcn Dialog)
//
// ── Story 53.2 (E53 / FR26-VIEW-1) — mature viewer ────────────────────────
// Zoom / pan / double-tap, plus the three VISIBLE single-pointer controls that
// make every gesture-reachable state reachable without a gesture (WCAG 2.2
// SC 2.5.1 + SC 2.5.7). The structural decision is THREE layers, not two
// (`EXPERIENCE.md:234`, `DESIGN.md:286, :299`, mockup `key-viewer-chrome.html`
// state C):
//
//   1. transform layer — ONLY the `renderImage(...)` output; scales/translates
//   2. chrome layer    — counter / close / chevrons; fades on tap-to-hide
//   3. toolbar layer   — Zoom In / Zoom Out / Reset; ALWAYS mounted, always
//                        visible, never `aria-hidden`, outside both 1 and 2
//
// Layer 3 is the whole point: a zoomed, one-handed user who has tapped the
// chrome away must still be able to get back to 1.0.
//
// Scroll lock is NOT implemented here. `@base-ui/react`'s `Dialog.Root`
// defaults `modal: true`, which runs `useScrollLock` with save/restore of the
// document's inline overflow (story V-2). Stacking a second lock on top of a
// working one is worse than either; this story VERIFIES it instead
// (`image-viewer-zoom.spec.ts`).

import { ChevronLeft, ChevronRight, Maximize2, Minus, Plus, X } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Dialog, DialogContent, DialogTitle } from "@/ui/dialog";
import { cn } from "@/lib/utils";

import type { ImageFullscreenViewerProps } from "./types";
import type { Vec2 } from "./zoom";
import {
  BASE_MAX_SCALE,
  MIN_SCALE,
  clampPan,
  clampScale,
  doubleTapTarget,
  panForScaleAbout,
  resolveMaxScale,
  zoomIn,
  zoomOut,
} from "./zoom";

// Swipe-distance threshold (px) before we treat a touch drag as a
// horizontal-navigation gesture. 50px matches what the broader React
// ecosystem uses for carousel components (e.g. embla-carousel default)
// and is comfortably above accidental-thumb-drift noise.
const SWIPE_THRESHOLD_PX = 50;
// Maximum |y| drift permitted on a horizontal swipe — beyond this we
// assume the user is scrolling vertically (e.g. the thumb strip), not
// navigating. Designer §5 noted pinch + swipe-down-close are deferred;
// this disambiguation keeps the deferred work from getting tangled up.
const SWIPE_VERTICAL_TOLERANCE_PX = 60;
// Story 53.2 — a release counts as a TAP only if the finger stayed inside this
// radius. It exists solely to keep a deliberate pan (which only happens at
// scale > 1.0) from being read as a tap and flipping the chrome underneath the
// user (D-2/D-3). It is NOT consulted on the scale-1.0 path, so the four-cell
// gesture matrix TB-043 closed is untouched.
const TAP_MOVE_TOLERANCE_PX = 10;
// Two taps are one double-tap when they land within this window...
const DOUBLE_TAP_WINDOW_MS = 300;
// ...and within one minimum touch target of each other. 44 is
// `{spacing.target-fullscreen-close}` (`DESIGN.md:287`, `EXPERIENCE.md:302`) —
// the same floor the close control uses, reused rather than invented.
const DOUBLE_TAP_SLOP_PX = 44;
// Story 53.3 D-5 — readiness stall -> reported failure.
//
// The `/share` renderer resolves its blob into an object URL and renders a
// placeholder `<div>` until it has one; when `acquireShareBlob` rejects
// (404 / 429 / offline) the rejection is SWALLOWED and no `<img>` is ever
// mounted at all. Neither `load` nor `error` can fire on an element that does
// not exist, so no listener-based repair can reach that path — a timeout is
// the only mechanism that can (story V-12).
//
// Story 53.3 code review DN-2 (controller-accepted repair, 2026-07-31) — the
// watchdog is armed ONLY on that never-mounted-`<img>` branch. It used to arm
// on the ordinary `<img>` path too, where `load` / `error` normally answer for
// themselves: a slow-but-working photo was therefore painted over with the
// inline error and ANNOUNCED as failed at 15 s, and the recovery was silent
// (an emptied `aria-live` region announces nothing). D-5's stated contract —
// "convert an UNREPORTED stall into a reported failure" — is what this
// narrowing restores; D-5's literal mechanism wording ("arm whenever the
// resolved status is `loading`") is the part that is deliberately not
// followed.
//
// The narrowing is a ruled TRADEOFF, not a categorical claim: a mounted
// `<img>` whose request is black-holed or hangs indefinitely fires neither
// `load` nor `error` until the network stack gives up, so that stall IS
// unreported and is no longer converted. Accepted because the alternative
// condemned every slow-but-valid photo, and the mounted-and-hung residual is
// ledgered OPEN in `deferred-work.md` rather than asserted out of existence.
//
// The contract this number serves is "convert an unreported stall into a
// reported failure", NOT "police latency":
//   - FLOOR: `shareBlobCache`'s `MAX_CONCURRENT_FETCHES = 4` semaphore queues
//     overflow callers, and nothing below it has a timeout or an
//     `AbortController` of its own — a strip burst can leave one image queued
//     behind several batches before its fetch is even dispatched (V-13).
//     15 s is far above that on any working connection.
//   - CEILING: well inside the window where total silence reads as "broken",
//     and far below the indefinite wait that is today's behaviour.
// It is not a latency SLO: do not tune it to make a slow test faster, and do
// not add a retry — retry policy belongs to `shareBlobCache`, which owns the
// rate-limit and semaphore invariants and which this story must not touch.
const IMAGE_READY_TIMEOUT_MS = 15_000;

const ORIGIN: Vec2 = { x: 0, y: 0 };

type ImageStatus = "loading" | "ready" | "error";

// Structural, not `Touch`: React's synthetic `React.Touch` is a narrower type
// than the DOM's and the two are not assignable to each other.
interface ClientPoint {
  readonly clientX: number;
  readonly clientY: number;
}

function touchDistance(a: ClientPoint, b: ClientPoint): number {
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

export default function ImageFullscreenViewer({
  sources,
  initialIndex,
  onClose,
  renderImage,
  // Story 22.3 round-2 (Codex P1): when the consumer supplies a
  // separate thumb renderer, use it for the strip. Defaults to
  // `renderImage`, preserving the single-renderer shape for the
  // simple /catalog/<id> mount. ShareCarousel injects
  // `LazyAnonymousImage` here so strip thumbs lazy-load on
  // IntersectionObserver instead of all fetching at viewer-open.
  renderThumb,
}: ImageFullscreenViewerProps) {
  const { t } = useTranslation();
  const renderThumbResolved = renderThumb ?? renderImage;

  // Clamp initialIndex defensively: a consumer passing an out-of-range
  // index (e.g. after deletion races) would otherwise render undefined.
  const safeInitial =
    sources.length === 0
      ? 0
      : Math.max(0, Math.min(initialIndex, sources.length - 1));
  const [activeIdx, setActiveIdx] = useState(safeInitial);

  // Mobile tap-to-toggle chrome — when false, hide counter/chevrons/close
  // so the user sees the image edge-to-edge. Re-shows on tap (and on every
  // arrow-key navigation, so keyboard users never lose the close button).
  const [chromeVisible, setChromeVisible] = useState(true);

  // Touch tracking for swipe-LR. We deliberately do NOT attach onMouseDown
  // — desktop users have chevrons + arrow keys; pointer drags would
  // conflict with click-to-toggle-chrome on track-pad clicks.
  // Story 28.2 (Init 17 / TB-043 round-3 follow-up): capture
  // `stripOrigin` flag from coords (not target.contains) so the gesture
  // guard works whether the strip is interactive (chrome visible) OR
  // pointer-events-none (chrome hidden, Story 22.3 round-3 patch). On
  // hidden-strip drag, target is the viewer root (passes through) but
  // touch coordinates still land inside the strip's bounding rect, so
  // coords-check correctly suppresses step() while still letting the
  // SHORT-tap path toggle chrome.
  const touchStart = useRef<{
    x: number;
    y: number;
    stripOrigin: boolean;
    thumbOrigin: boolean;
    // Story 53.2 D-2: a tap that lands on the always-mounted zoom toolbar must
    // neither toggle chrome nor be read as a swipe. Same narrow `closest()`
    // technique as `thumbOrigin`, deliberately NOT a widening of the
    // coords-based `stripOrigin` check.
    toolbarOrigin: boolean;
    panX: number;
    panY: number;
  } | null>(null);

  // ── Story 53.2 — zoom + pan state ───────────────────────────────────────
  // Rendered from state; read from refs inside the touch handlers, which run
  // outside React's render cycle and would otherwise close over stale values
  // mid-gesture.
  const [scale, setScale] = useState(MIN_SCALE);
  const [pan, setPan] = useState<Vec2>(ORIGIN);
  const [maxScale, setMaxScale] = useState(BASE_MAX_SCALE);
  const [imageStatus, setImageStatus] = useState<ImageStatus>("loading");
  // True once the user has actually MOVED the zoom on the current image. It
  // gates the polite announcement: `EXPERIENCE.md:318` announces zoom level
  // *changes*, and an image resolving at 1.0 is not one — without this, arrowing
  // through a 20-photo gallery emits 20 unasked-for "Zoom 100%"s.
  const zoomTouchedRef = useRef(false);
  const scaleRef = useRef(MIN_SCALE);
  const panRef = useRef<Vec2>(ORIGIN);
  const maxScaleRef = useRef(BASE_MAX_SCALE);
  // The frame is tracked BOTH as a ref (read synchronously inside the touch
  // handlers) and as state (so the load/error effect below re-runs once the
  // node exists). Base UI PORTALS the dialog popup, so on the first effect
  // pass `frameRef.current` is still null — a plain ref would silently never
  // attach the load listener and pin the toolbar disabled forever.
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [frameEl, setFrameEl] = useState<HTMLDivElement | null>(null);
  const attachFrame = useCallback((node: HTMLDivElement | null) => {
    frameRef.current = node;
    setFrameEl(node);
  }, []);
  const layerRef = useRef<HTMLDivElement | null>(null);
  // A pinch in progress: the finger separation, scale and pan at the moment
  // the second finger landed, plus the midpoint to scale about.
  const pinchRef = useRef<{ distance: number; scale: number; pan: Vec2; focus: Vec2 } | null>(
    null,
  );
  // Set as soon as a gesture actually moves the image. A moved gesture is
  // never a tap and never navigates.
  const gestureMovedRef = useRef(false);
  const lastTapRef = useRef<{ at: number; x: number; y: number } | null>(null);

  // Cap activeIdx if the parent re-feeds a shorter sources array between
  // renders (e.g. on photo delete). Keep us pointing at a valid entry.
  const lastLen = useRef(sources.length);
  if (lastLen.current !== sources.length) {
    lastLen.current = sources.length;
    if (activeIdx >= sources.length && sources.length > 0) {
      setActiveIdx(sources.length - 1);
    }
  }

  const total = sources.length;
  const active = sources[activeIdx];
  const showNav = total > 1;

  // Scroll the active thumb into view whenever activeIdx changes so the
  // strip never desyncs from the main frame on long galleries. jsdom does
  // not ship `Element.prototype.scrollIntoView` — guard with typeof so the
  // viewer keeps rendering inside vitest, where the call is a no-op.
  const stripRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const strip = stripRef.current;
    if (strip === null) return;
    const thumb = strip.querySelector<HTMLButtonElement>(
      `[data-thumb-idx="${activeIdx}"]`,
    );
    if (thumb !== null && typeof thumb.scrollIntoView === "function") {
      thumb.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
    }
  }, [activeIdx]);

  // ── Story 53.2 — zoom engine ────────────────────────────────────────────

  /** The rendered `<img>` inside the transform layer, whoever rendered it.
   *  `null` while `AnonymousImage` is still resolving its blob (/share). */
  const currentImage = useCallback(
    (): HTMLImageElement | null => layerRef.current?.querySelector("img") ?? null,
    [],
  );

  /**
   * Commit a scale + pan pair. Clamping lives here so EVERY entry point —
   * buttons, keys, pinch, double-tap, resize — re-clamps against the same
   * measured geometry (D-4: "the clamp is re-evaluated after a zoom change so
   * a zoom-out can never leave the image detached from an edge").
   *
   * `offsetWidth`/`offsetHeight` (not `getBoundingClientRect`) give the image's
   * UNSCALED layout box — the CSS transform does not affect them, which is
   * exactly what the clamp maths needs.
   */
  const commit = useCallback(
    (nextScale: number, nextPan: Vec2) => {
      const frame = frameRef.current;
      const img = currentImage();
      const s = clampScale(nextScale, maxScaleRef.current);
      const p = clampPan(
        nextPan,
        s,
        { width: img?.offsetWidth ?? 0, height: img?.offsetHeight ?? 0 },
        { width: frame?.clientWidth ?? 0, height: frame?.clientHeight ?? 0 },
      );
      if (s !== scaleRef.current) zoomTouchedRef.current = true;
      scaleRef.current = s;
      panRef.current = p;
      setScale(s);
      setPan(p);
    },
    [currentImage],
  );

  /** Scale about a focus point expressed relative to the frame centre. */
  const zoomAbout = useCallback(
    (nextScale: number, focus: Vec2) => {
      const from = scaleRef.current;
      const to = clampScale(nextScale, maxScaleRef.current);
      commit(to, panForScaleAbout(panRef.current, from, to, focus));
    },
    [commit],
  );

  const canZoom = imageStatus === "ready";
  const atMinScale = scale <= MIN_SCALE;
  const atMaxScale = scale >= maxScale;

  // A zoom control that disables itself under the user's own finger is blurred
  // by the browser, and focus falls to `<body>` — MEASURED in Chromium, not
  // assumed, and Base UI's focus manager does not recover it. That strands a
  // keyboard / switch user outside the toolbar inside a focus-trapped dialog
  // (NFR26-A11Y-1). Remember which toolbar control acted, and if the render it
  // triggered disabled that control, hand focus to the sibling still live.
  const toolbarRef = useRef<HTMLDivElement | null>(null);
  const actingControlRef = useRef<HTMLButtonElement | null>(null);
  const rememberActingControl = useCallback(() => {
    const el = document.activeElement;
    const bar = toolbarRef.current;
    actingControlRef.current =
      el instanceof HTMLButtonElement && bar !== null && bar.contains(el) ? el : null;
  }, []);
  useLayoutEffect(() => {
    const acted = actingControlRef.current;
    actingControlRef.current = null;
    if (acted === null || !acted.disabled) return;
    if (document.activeElement !== document.body) return;
    const next = toolbarRef.current
      ?.querySelector<HTMLButtonElement>("button:not([disabled])");
    next?.focus();
  });

  const handleZoomIn = useCallback(() => {
    if (imageStatus !== "ready") return;
    rememberActingControl();
    zoomAbout(zoomIn(scaleRef.current, maxScaleRef.current), ORIGIN);
  }, [imageStatus, rememberActingControl, zoomAbout]);

  const handleZoomOut = useCallback(() => {
    if (imageStatus !== "ready") return;
    rememberActingControl();
    zoomAbout(zoomOut(scaleRef.current, maxScaleRef.current), ORIGIN);
  }, [imageStatus, rememberActingControl, zoomAbout]);

  const handleZoomReset = useCallback(() => {
    if (imageStatus !== "ready") return;
    rememberActingControl();
    commit(MIN_SCALE, ORIGIN);
  }, [commit, imageStatus, rememberActingControl]);

  /** Translate a touch point into the transform's coordinate space. */
  const focusOf = useCallback((clientX: number, clientY: number): Vec2 => {
    const frame = frameRef.current;
    if (frame === null) return ORIGIN;
    const r = frame.getBoundingClientRect();
    return { x: clientX - (r.left + r.width / 2), y: clientY - (r.top + r.height / 2) };
  }, []);

  // Load / error observation (D-6). `load` and `error` do not bubble but they
  // DO capture, so a capture-phase listener on the frame learns when the
  // descendant <img> resolved without touching `renderImage`, its call sites,
  // `AnonymousImage` or `shareBlobCache` (V-12 — that boundary is untouchable).
  // Re-armed on every activeIdx change, which is also where zoom resets.
  useEffect(() => {
    scaleRef.current = MIN_SCALE;
    panRef.current = ORIGIN;
    lastTapRef.current = null;
    zoomTouchedRef.current = false;
    // A gesture in flight when the image changes belongs to the OLD image. The
    // pinch snapshot in particular is absolute (finger separation -> scale), so
    // leaving it armed would re-apply the previous photo's zoom to the new,
    // still-loading one — with all three controls disabled and no way back.
    pinchRef.current = null;
    touchStart.current = null;
    gestureMovedRef.current = false;
    setScale(MIN_SCALE);
    setPan(ORIGIN);

    const frame = frameEl;
    if (frame === null) return undefined;

    const measureMaxScale = (img: HTMLImageElement) => {
      const next = resolveMaxScale(img.naturalWidth, img.offsetWidth);
      maxScaleRef.current = next;
      setMaxScale(next);
    };

    // Story 53.3 D-5 — the readiness watchdog. Armed only on the branch where
    // NO `<img>` is mounted at all (DN-2), and torn down by `load`, by
    // `error`, by an `activeIdx` change (this effect re-runs, so cleanup
    // fires) and by unmount. A leaked timer must never fire onto a LATER
    // image. `load`/`error` still reach it after a late `<img>` mounts,
    // because the capture listener lives on the frame, not on the element.
    let readyTimeout: ReturnType<typeof setTimeout> | undefined;
    const clearReadyTimeout = () => {
      if (readyTimeout !== undefined) {
        clearTimeout(readyTimeout);
        readyTimeout = undefined;
      }
    };
    const armReadyTimeout = () => {
      clearReadyTimeout();
      readyTimeout = setTimeout(() => {
        readyTimeout = undefined;
        setImageStatus("error");
      }, IMAGE_READY_TIMEOUT_MS);
    };

    // Initial probe. `complete` covers the already-cached image, whose `load`
    // fired before this listener existed. A `null` img means /share's
    // `AnonymousImage` is still resolving its blob and has rendered a
    // placeholder instead.
    const initial = frame.querySelector("img");
    if (initial === null) {
      // No `<img>` at all — the /share placeholder case. Nothing will ever
      // fire here, so the watchdog is the ONLY path out of `loading` (D-5).
      setImageStatus("loading");
      armReadyTimeout();
    } else if (!initial.complete) {
      // An `<img>` IS mounted, so `load` or `error` normally answers for it —
      // the watchdog is deliberately NOT armed here (DN-2). Arming it made a
      // slow-but-valid photo report as a terminal failure at 15 s while it was
      // still downloading; staying `loading` is both true and recoverable,
      // which is what `EXPERIENCE.md:259` asks for. The accepted cost is a
      // request that is black-holed rather than slow: it fires neither event
      // and stays `loading` indefinitely (ledgered OPEN, see the constant).
      setImageStatus("loading");
    } else {
      // `complete` is ALSO true for an image that already FAILED, and its
      // `error` event fired before this listener existed — so `complete` alone
      // would arm the zoom controls over a broken image and announce "100%" for
      // nothing. `naturalWidth > 0` is what separates the two.
      setImageStatus(initial.naturalWidth > 0 ? "ready" : "error");
      measureMaxScale(initial);
    }

    // The `load` EVENT is the readiness signal in its own right — do not
    // re-consult `complete` here. jsdom never fetches resources and reports
    // `complete === false` forever, so re-deriving readiness from it would
    // pin the toolbar disabled and make this whole path untestable.
    const onLoad = (ev: Event) => {
      if (ev.target instanceof HTMLImageElement) {
        // Unconditional, and deliberately so: a `load` arriving AFTER the
        // watchdog fired still restores `ready`. The timeout REPORTS a stall,
        // it does not permanently condemn the image (D-5).
        clearReadyTimeout();
        setImageStatus("ready");
        measureMaxScale(ev.target);
      }
    };
    const onError = (ev: Event) => {
      // A failed image never traps the user: close + toolbar stay mounted and
      // reachable, the zoom controls simply have nothing to act on.
      if (ev.target instanceof HTMLImageElement) {
        clearReadyTimeout();
        setImageStatus("error");
      }
    };
    frame.addEventListener("load", onLoad, true);
    frame.addEventListener("error", onError, true);
    return () => {
      clearReadyTimeout();
      frame.removeEventListener("load", onLoad, true);
      frame.removeEventListener("error", onError, true);
    };
  }, [activeIdx, frameEl]);

  // Polite announcement text (D-7 / D-6). Held in STATE and written from an
  // effect on purpose: an `aria-live` region never announces the content it was
  // INSERTED with, only later mutations — and Base UI portals this whole subtree
  // in at once, so anything rendered on the first pass is silent. Mounting empty
  // and filling it here is what makes the loading state genuinely ANNOUNCED
  // rather than merely dimmed (`EXPERIENCE.md:259`).
  const [announcement, setAnnouncement] = useState("");
  useEffect(() => {
    if (imageStatus === "loading") {
      setAnnouncement(t("catalog.image_viewer.loading"));
      return;
    }
    // Story 53.3 D-6 — a failure used to fall through to `""`, so a broken
    // image gave a blank frame and total silence. It is announced from state
    // for the same reason the loading text is: an `aria-live` region never
    // announces the content it was INSERTED with, and Base UI portals this
    // whole subtree in at once.
    if (imageStatus === "error") {
      setAnnouncement(t("catalog.image_viewer.error"));
      return;
    }
    if (imageStatus === "ready" && zoomTouchedRef.current) {
      setAnnouncement(
        t("catalog.image_viewer.zoom_level", { percent: Math.round(scale * 100) }),
      );
      return;
    }
    setAnnouncement("");
  }, [imageStatus, scale, t]);

  // Rotation / resize: re-fit to the new viewport PRESERVING the zoom level and
  // re-clamping pan (`EXPERIENCE.md:262`) — never leave the image outside the
  // visible area.
  useEffect(() => {
    const onViewportChange = () => {
      const img = currentImage();
      // Only re-derive the ceiling from geometry that actually MEASURES. On
      // /share the renderer swaps in a placeholder while it re-resolves its
      // blob, and mid-decode `offsetWidth` is 0 — `resolveMaxScale` answers
      // BASE_MAX_SCALE for both, so re-deriving here would silently demote a
      // panorama's 20x ceiling to 4x and drag the user's zoom down with it,
      // with nothing to restore it (the measure path is keyed on activeIdx).
      // "Unmeasurable" is not "4".
      if (img !== null && img.naturalWidth > 0 && img.offsetWidth > 0) {
        const next = resolveMaxScale(img.naturalWidth, img.offsetWidth);
        maxScaleRef.current = next;
        setMaxScale(next);
      }
      commit(scaleRef.current, panRef.current);
    };
    window.addEventListener("resize", onViewportChange);
    window.addEventListener("orientationchange", onViewportChange);
    return () => {
      window.removeEventListener("resize", onViewportChange);
      window.removeEventListener("orientationchange", onViewportChange);
    };
  }, [commit, currentImage]);

  function step(delta: number) {
    if (total === 0) return;
    setActiveIdx((i) => (i + delta + total) % total);
    setChromeVisible(true);
  }

  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // ESC: let the Dialog default fire (it'll call our `onOpenChange`
    // closer). We don't intercept here.
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      e.stopPropagation();
      step(-1);
      return;
    }
    if (e.key === "ArrowRight") {
      e.preventDefault();
      e.stopPropagation();
      step(1);
      return;
    }
    // Story 53.2 (AC-2) — `+` / `-` / `0` perform EXACTLY the three toolbar
    // actions (`EXPERIENCE.md:282`: key and button are the same action), so no
    // zoomed state is reachable by gesture alone.
    //
    // ...but ONLY unmodified. `Ctrl`/`Cmd` + `+`/`-`/`0` are the browser's own
    // page-zoom shortcuts, Chromium lets a keydown handler cancel them, and
    // `preventDefault()` below is unconditional — so without this guard opening
    // the viewer would take page zoom away from exactly the low-vision user
    // this story exists for (WCAG 1.4.4). `Alt` is excluded for the same reason:
    // it is a modifier this viewer does not own.
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "+") {
      e.preventDefault();
      e.stopPropagation();
      handleZoomIn();
      return;
    }
    if (e.key === "-") {
      e.preventDefault();
      e.stopPropagation();
      handleZoomOut();
      return;
    }
    if (e.key === "0") {
      e.preventDefault();
      e.stopPropagation();
      handleZoomReset();
      return;
    }
  };

  const onTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    const t0 = e.touches[0];
    if (t0 === undefined) return;
    // Story 28.2 (Init 17 / TB-043): coords-based stripOrigin check.
    // Compare touch clientY to strip's bounding rect vertical bounds
    // (works whether strip is interactive OR pointer-events-none —
    // hidden-strip touches DO reach the viewer root via pass-through
    // but their coordinates still land inside strip bounds, so the
    // guard fires correctly). Previous `strip.contains(e.target)`
    // check missed the hidden-strip case because target was the
    // viewer root (Story 22.3 round-3 Codex P3).
    let stripOrigin = false;
    const strip = stripRef.current;
    if (strip !== null) {
      const rect = strip.getBoundingClientRect();
      if (t0.clientY >= rect.top && t0.clientY <= rect.bottom) {
        stripOrigin = true;
      }
    }
    // Story 28.2 round-3 (Init 17 / Codex P2): thumbOrigin is the NARROW
    // signal for chrome-toggle deferral. Only actual thumb-button taps
    // (data-thumb-idx="N") need to defer the chrome flip to the thumb's
    // own onClick handler. Padded/empty strip areas (gap-1.5, px-3, py-2)
    // had stripOrigin=true but no thumb to defer to, creating dead-zone
    // taps that never toggled chrome. thumbOrigin is naturally false in
    // the hidden-strip state because the strip is `pointer-events-none`
    // and e.target is the viewer root, so the chrome-restore path on
    // hidden-strip taps still fires correctly.
    const target = e.target;
    const thumbOrigin =
      target instanceof Element && target.closest("[data-thumb-idx]") !== null;
    // Story 53.2 D-2 — same narrow technique, third origin case.
    const toolbarOrigin =
      target instanceof Element &&
      target.closest('[data-testid="image-viewer-toolbar"]') !== null;

    // Second finger down → this is a pinch. Snapshot the separation, the
    // current transform and the midpoint to scale about.
    const t1 = e.touches[1];
    if (t1 !== undefined) {
      // A two-finger gesture is never a tap and never navigates — set this
      // BEFORE the readiness/distance guards, so a pinch on a still-loading
      // image cannot fall through and be released as a swipe.
      gestureMovedRef.current = true;
      const distance = touchDistance(t0, t1);
      if (distance > 0 && imageStatus === "ready") {
        pinchRef.current = {
          distance,
          scale: scaleRef.current,
          pan: panRef.current,
          focus: focusOf((t0.clientX + t1.clientX) / 2, (t0.clientY + t1.clientY) / 2),
        };
      }
      return;
    }

    pinchRef.current = null;
    gestureMovedRef.current = false;
    touchStart.current = {
      x: t0.clientX,
      y: t0.clientY,
      stripOrigin,
      thumbOrigin,
      toolbarOrigin,
      panX: panRef.current.x,
      panY: panRef.current.y,
    };
  };

  // Story 53.2 T3 / V-18 — this handler NEVER calls `preventDefault()`. React
  // registers `touchstart` / `touchmove` / `wheel` as PASSIVE at the root
  // (verified in the installed react-dom 19.2.6 bundle), so a `preventDefault`
  // here is silently ignored and the browser keeps scrolling underneath. The
  // browser default is suppressed DECLARATIVELY instead, by `touch-action:
  // none` scoped to the transform layer only (see the render below and V-19).
  const onTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    const pinch = pinchRef.current;
    const t0 = e.touches[0];
    const t1 = e.touches[1];

    if (pinch !== null && t0 !== undefined && t1 !== undefined) {
      const distance = touchDistance(t0, t1);
      if (distance <= 0) return;
      // Derived from the PINCH SNAPSHOT, not from the live refs, so the
      // gesture stays absolute (finger separation -> scale) instead of
      // accumulating rounding drift frame by frame.
      const to = clampScale((pinch.scale * distance) / pinch.distance, maxScaleRef.current);
      commit(to, panForScaleAbout(pinch.pan, pinch.scale, to, pinch.focus));
      return;
    }

    // Single-pointer drag at scale > 1.0 PANS and never navigates (D-3).
    const start = touchStart.current;
    if (t0 === undefined || start === null) return;
    if (scaleRef.current <= MIN_SCALE) return;
    if (start.stripOrigin || start.thumbOrigin || start.toolbarOrigin) return;
    const dx = t0.clientX - start.x;
    const dy = t0.clientY - start.y;
    if (Math.hypot(dx, dy) > TAP_MOVE_TOLERANCE_PX) gestureMovedRef.current = true;
    commit(scaleRef.current, { x: start.panX + dx, y: start.panY + dy });
  };

  const onTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    // Wait for the LAST finger to lift. Without this a pinch release would
    // reach the swipe branch below with a single-touch origin and could
    // navigate; the shipped single-finger paths are unaffected because their
    // `touchend` already fires with zero remaining touches.
    if (e.touches.length > 0) {
      // The gesture continues with fewer fingers. Re-baseline the drag origin
      // to the remaining finger AND to the pan the pinch actually left behind,
      // otherwise the next `onTouchMove` would compute its offset from the
      // pre-pinch baseline and snap the image back. `gestureMovedRef`
      // deliberately stays true, so the eventual release still cannot be read
      // as a tap or a swipe.
      const remaining = e.touches[0];
      if (remaining !== undefined) {
        const start = touchStart.current;
        // `start` is null when the gesture OPENED with two coalesced fingers:
        // `onTouchStart`'s pinch branch returns before writing it. Synthesise
        // one rather than requiring it, or the remaining finger would be unable
        // to pan at all (`onTouchMove` bails on `start === null`) and the user
        // would have to lift completely and start again.
        touchStart.current = {
          stripOrigin: start?.stripOrigin ?? false,
          thumbOrigin: start?.thumbOrigin ?? false,
          toolbarOrigin: start?.toolbarOrigin ?? false,
          x: remaining.clientX,
          y: remaining.clientY,
          panX: panRef.current.x,
          panY: panRef.current.y,
        };
      }
      // Only tear the pinch down once fewer than two fingers remain. Lifting a
      // resting third finger mid-pinch leaves two fingers still pinching; the
      // old unconditional teardown converted the rest of that gesture into a
      // single-pointer pan and `onTouchStart` never fires again to re-arm it.
      const a = e.touches[0];
      const b = e.touches[1];
      if (a !== undefined && b !== undefined && imageStatus === "ready") {
        const distance = touchDistance(a, b);
        if (distance > 0) {
          pinchRef.current = {
            distance,
            scale: scaleRef.current,
            pan: panRef.current,
            focus: focusOf((a.clientX + b.clientX) / 2, (a.clientY + b.clientY) / 2),
          };
          return;
        }
      }
      pinchRef.current = null;
      return;
    }

    const start = touchStart.current;
    const wasPinch = pinchRef.current !== null;
    const moved = gestureMovedRef.current;
    touchStart.current = null;
    pinchRef.current = null;
    gestureMovedRef.current = false;
    if (start === null) return;
    const t0 = e.changedTouches[0];
    if (t0 === undefined) return;
    // D-2: a toolbar tap neither toggles chrome nor navigates — the button's
    // own onClick owns it. It also BREAKS any double-tap in progress: without
    // clearing the pending tap, "tap image, press Zoom in, tap image" inside one
    // 300 ms window reads as a double-tap and throws away the zoom just applied.
    if (start.toolbarOrigin) {
      lastTapRef.current = null;
      return;
    }
    // A pinch or a real pan is neither a tap nor a swipe.
    if (wasPinch || moved) return;
    const dx = t0.clientX - start.x;
    const dy = t0.clientY - start.y;
    // Disambiguation: if the vertical drift dominates, treat as scroll —
    // don't intercept. Pinch-zoom + swipe-down-close stay deferred.
    if (Math.abs(dy) > SWIPE_VERTICAL_TOLERANCE_PX) return;
    if (Math.abs(dx) < SWIPE_THRESHOLD_PX) {
      // Short tap — toggle chrome visibility (designer §5).
      //
      // Story 28.2 round-3 (Codex P2): defer chrome toggle ONLY when the
      // touch landed on an actual thumb button (data-thumb-idx). Otherwise
      // padded/empty areas of the visible strip become dead-zone taps that
      // never toggle chrome. thumbOrigin already implies the visible state
      // (hidden strip is pointer-events-none → closest('[data-thumb-idx]')
      // returns null → thumbOrigin=false → chrome toggles normally to
      // restore overlay).
      if (start.thumbOrigin) {
        // Same double-tap break as the toolbar case above.
        lastTapRef.current = null;
        return;
      }
      // Story 53.2 (D-3) — double-tap toggles 1.0 <-> the fixed step, about
      // the tapped point. It is a CONVENIENCE: `doubleTapTarget` sits on the
      // Zoom In ladder, so every state it reaches is also reachable with the
      // visible controls (AC-2). The first tap of the pair already flipped the
      // chrome, so flip it back — a double-tap must zoom, not disturb chrome.
      const last = lastTapRef.current;
      if (
        imageStatus === "ready" &&
        last !== null &&
        e.timeStamp - last.at <= DOUBLE_TAP_WINDOW_MS &&
        Math.hypot(t0.clientX - last.x, t0.clientY - last.y) <= DOUBLE_TAP_SLOP_PX
      ) {
        lastTapRef.current = null;
        setChromeVisible((v) => !v);
        zoomAbout(
          doubleTapTarget(scaleRef.current, maxScaleRef.current),
          focusOf(t0.clientX, t0.clientY),
        );
        return;
      }
      lastTapRef.current = { at: e.timeStamp, x: t0.clientX, y: t0.clientY };
      setChromeVisible((v) => !v);
      return;
    }
    // Story 53.2 (D-3, AC-3) — at scale > 1.0 a horizontal drag ALWAYS pans
    // and NEVER navigates; the pan itself already happened in `onTouchMove`.
    // Navigation stays available via the chevrons, the thumb strip and the
    // arrow keys, and Reset returns to 1.0 which re-arms swipe navigation.
    if (scaleRef.current > MIN_SCALE) return;
    // Story 28.2 (Init 17 / TB-043): strip-origin drags never navigate.
    // Either the visible strip is being scrolled (native overflow-x-auto)
    // OR the hidden strip area was touched (chrome-restore via the SHORT
    // path above already fired if it was a tap). Suppressing step() here
    // closes the round-3 Codex P3.
    if (start.stripOrigin) return;
    // Long horizontal swipe — navigate. dx < 0 = swipe-left = next image.
    if (total > 1) {
      step(dx < 0 ? 1 : -1);
    }
  };

  if (active === undefined) {
    // Sources empty — nothing to render. Parent should never open the
    // viewer in this state, but cover it for safety.
    return null;
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        showCloseButton={false}
        // E48.1 — geometry is anchored to the viewport origin instead of
        // inheriting `dialog.tsx`'s `left-1/2 top-1/2 -translate-*` centering.
        // That centering mixes two different reference boxes: `left: 50%`
        // resolves against the fixed-position containing block (mobile Chrome's
        // LAYOUT viewport, which it widens to the document's scroll width the
        // moment the page overflows horizontally) while `w-[98vw]` resolves
        // against the VISUAL viewport. Once the two diverge the dialog is
        // displaced sideways and the top-right close button leaves the visible
        // area — the reported "only the left half is visible and I can't get
        // out" trap. Expressing offset and size in the same unit makes the
        // geometry drift-proof; on a non-overflowing viewport `1vw`/`2.5dvh`
        // are the same insets the centered layout produced, so the change is
        // sub-pixel (it did re-rasterise the close glyph in the two mobile
        // baselines — 32 px / 19 px — but moved no box edge).
        //
        // `max-w-[calc(100%-2vw)]` is the counterweight to that anchoring.
        // `vw` counts the classic-scrollbar gutter, `100%` (the containing
        // block) does not, so on a platform with non-overlay scrollbars a
        // plain `left:1vw + width:98vw` would push the right edge — and the
        // close button on it — past the visible area by the gutter width.
        // The old centered form absorbed that deficit by splitting it across
        // both edges; anchoring to the left does not, hence the explicit cap.
        // It is inert wherever the gutter is 0 (`100% == 100vw`, so the cap
        // equals `98vw`), which is why headless CI cannot exercise it —
        // Chromium here uses overlay scrollbars (measured: clientWidth ==
        // innerWidth == 100vw == 1280).
        //
        // `dvh` (not `vh`) for the height budget: on a phone `vh` is the LARGE
        // viewport — measured with the browser toolbar hidden — so `95vh`
        // overshoots the area the user can actually see whenever the toolbar
        // is showing. `dvh` tracks the visible area. (Headless Chromium has no
        // dynamic toolbar, so this is reasoned, not test-covered.)
        className="h-[95dvh] w-[98vw] max-w-[calc(100%-2vw)] left-[1vw] top-[2.5dvh] translate-x-0 translate-y-0 p-0 outline-none bg-background/95 backdrop-blur-sm sm:max-w-[calc(100%-2vw)]"
        onKeyDown={onKey}
      >
        <DialogTitle className="sr-only">
          {t("catalog.image_viewer.dialog_title")}
        </DialogTitle>

        <div
          data-testid="image-viewer-root"
          className="relative flex h-full w-full flex-col"
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        >
          {/* Main frame fills available space; thumb strip sits below.
              Story 26.1 (Init 17 / TB-044): `min-h-0` is the canonical
              flexbox trick to allow the main-frame container to SHRINK
              below the intrinsic size of its content (large images).
              Without it, the `<img>`'s intrinsic 4k/8k height would expand
              the flex item, pushing the strip + nav chevrons OFF the
              viewport on wide screens. */}
          <div
            ref={attachFrame}
            data-testid="image-viewer-frame"
            className="relative flex flex-1 min-h-0 items-center justify-center overflow-hidden"
          >
            {/* LAYER 1 — transform layer (Story 53.2 D-2). Wraps ONLY what
                `renderImage` returned; the viewer never inspects or replaces
                it, so the /share `AnonymousImage` credential boundary (V-12,
                NFR10-SHARE-SECURITY-1) is untouched.

                `touch-none` is `touch-action: none`, scoped to THIS ELEMENT.
                That is the declarative way to own the pinch/pan gesture, and
                it is required because React registers touch listeners as
                passive so `preventDefault()` from `onTouchMove` is a no-op
                (V-18/V-19). It is NOT `user-scalable=no`: that is a
                document-wide meta directive, it is banned by
                `EXPERIENCE.md:291` / `architecture.md:3374`, and
                `apps/web/index.html` is not touched by this story. Page-level
                pinch-zoom remains available everywhere outside this element.

                No transition on the transform: a pinch must track the fingers
                exactly, and an unconditional zoom animation is precisely the
                motion a `prefers-reduced-motion` user asked not to get. */}
            <div
              ref={layerRef}
              data-testid="image-viewer-transform"
              className="absolute inset-0 flex touch-none items-center justify-center"
              style={{
                transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${scale})`,
              }}
            >
              {renderImage({
                src: active.fullUrl,
                alt: active.alt,
                // Story 26.1 (Init 17 / TB-044): explicit max-h-[calc(95dvh-5rem)]
                // (DialogContent height = 95dvh; strip height = h-20 = 5rem)
                // so the image NEVER computes a height larger than the
                // available main-frame area. Combined with `min-h-0` above,
                // this keeps the strip + nav chevrons always in viewport
                // regardless of source image aspect ratio. E48.1 moved the unit
                // from `vh` to `dvh` so it keeps matching DialogContent's height.
                //
                // Story 53.2: the arithmetic is UNCHANGED and still correct.
                // The new toolbar layer is `absolute` inside this frame, so it
                // takes part in no flex layout and consumes none of the
                // vertical budget; the only in-flow siblings are still the
                // frame and the h-20 strip. Nothing to re-derive (T2/AC-8).
                className: "max-h-[calc(95dvh-5rem)] max-w-full object-contain",
              })}
            </div>

            {/* Story 53.3 D-6 — the inline error state (mockup
                `key-viewer-chrome.html` state E, `EXPERIENCE.md:260`). It sits
                INSIDE the frame but OUTSIDE the transform layer, so it neither
                scales nor pans with a zoom the user may have left applied, and
                it is `pointer-events-none` end to end so it can never swallow
                a tap meant for the close button, a chevron, the strip or the
                toolbar underneath it: a failed image never traps the user.
                Token-only colours — no new `--color-*` is authorised here. */}
            {imageStatus === "error" && (
              <div
                data-testid="image-viewer-error"
                className="pointer-events-none absolute inset-0 grid place-items-center px-6"
              >
                {/* DN-3 (controller-accepted repair, 2026-07-31): the backdrop
                    is `/60`, not `/40`. At `/40` the composite behind the white
                    copy measured rgb(151,151,151) in the LIGHT theme — 2.92:1,
                    under WCAG AA's 4.5:1 for 14 px text. `/60` composites to
                    rgb(102,102,102) ≈ 5.7:1 and stays inside D-6's
                    `gallery-control` token envelope (no new `--color-*`, no
                    literal). Dark theme was already ~20:1 and only deepens. */}
                <span className="rounded bg-gallery-control/60 px-3 py-2 text-center text-sm text-gallery-control-foreground">
                  {t("catalog.image_viewer.error")}
                </span>
              </div>
            )}

            {/* LAYER 2 — chrome layer: counter, close, chevrons. Fades when
                `chromeVisible` is false (mobile tap-to-hide). Story 53.2 does
                NOT change its semantics, and deliberately does NOT put the
                zoom toolbar inside it (`DESIGN.md:299`). */}
            <div
              className={cn(
                "pointer-events-none absolute inset-0 transition-opacity duration-150",
                chromeVisible ? "opacity-100" : "opacity-0",
              )}
              aria-hidden={!chromeVisible}
            >
              {showNav && (
                <div
                  data-testid="image-viewer-counter"
                  className="pointer-events-auto absolute left-3 top-3 rounded bg-background/60 px-2 py-1 text-sm text-muted-foreground"
                >
                  {t("catalog.image_viewer.counter", {
                    current: activeIdx + 1,
                    total,
                  })}
                </div>
              )}

              <button
                type="button"
                data-testid="image-viewer-close"
                onClick={() => onClose()}
                aria-label={t("catalog.image_viewer.close")}
                // Story 53.2 AC-4 — the close target moves 40x40 -> 44x44
                // (`h-11 w-11`), which is `{spacing.target-fullscreen-close}`
                // exactly (`DESIGN.md:180, :287`; `EXPERIENCE.md:302`; WCAG 2.2
                // SC 2.5.8). 44 rather than 48: it is the token's own value and
                // the smallest change that satisfies the floor.
                //
                // Story 53.2 D-5 — safe-area handling WITHOUT touching the
                // viewport meta. `env(safe-area-inset-*)` currently resolves to
                // 0 because `apps/web/index.html:5` carries no
                // `viewport-fit=cover` (V-3), and adding it is app-wide Ask
                // First. `max(0.75rem, env(...))` is therefore EXACTLY today's
                // `right-3`/`top-3` value — zero visual delta — and becomes
                // correct automatically if the meta ever opts in.
                className="pointer-events-auto absolute right-[max(0.75rem,env(safe-area-inset-right))] top-[max(0.75rem,env(safe-area-inset-top))] grid h-11 w-11 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60"
              >
                <X className="h-5 w-5" />
              </button>

              {showNav && (
                <>
                  <button
                    type="button"
                    data-testid="image-viewer-prev"
                    onClick={() => step(-1)}
                    aria-label={t("catalog.image_viewer.prev")}
                    className="pointer-events-auto absolute left-3 top-1/2 grid h-12 w-12 -translate-y-1/2 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60"
                  >
                    <ChevronLeft className="h-6 w-6" />
                  </button>
                  <button
                    type="button"
                    data-testid="image-viewer-next"
                    onClick={() => step(1)}
                    aria-label={t("catalog.image_viewer.next")}
                    className="pointer-events-auto absolute right-3 top-1/2 grid h-12 w-12 -translate-y-1/2 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60"
                  >
                    <ChevronRight className="h-6 w-6" />
                  </button>
                </>
              )}
            </div>

            {/* LAYER 3 — toolbar layer (Story 53.2 D-2 / AC-2). A SIBLING of
                the chrome layer, never a child: it is ALWAYS mounted, always
                visible, never `aria-hidden`, and never fades with
                `chromeVisible` (`EXPERIENCE.md:234`, `DESIGN.md:286, :299`,
                mockup state C — "the load-bearing state"). That is what keeps
                WCAG 2.2 SC 2.5.1 / SC 2.5.7 satisfiable for a zoomed,
                one-handed, chrome-hidden user.

                It also sits OUTSIDE the transform layer, so it keeps a
                constant size and position at every zoom level
                (`DESIGN.md` § Elevation & Depth).

                Centred with `inset-x-0` + `justify-center` rather than
                `left-1/2` + `-translate-x-1/2`: a single reference box, so the
                E48.1 invariant grep (`architecture.md:3371-3376`) stays
                literally clean on this file. Bottom inset carries the same
                `max(..., env(safe-area-inset-bottom))` forward-compatibility
                as the close button (D-5). */}
            <div className="pointer-events-none absolute inset-x-0 bottom-[max(1rem,env(safe-area-inset-bottom))] flex flex-col items-center gap-2">
              {/* Polite zoom announcement (D-7 / `EXPERIENCE.md:318`) — a zoom
                  with no visual frame of reference is otherwise silent. Also
                  the surface that finally wires the previously orphaned
                  `catalog.image_viewer.loading` key (V-4), which is how the
                  disabled toolbar is ANNOUNCED and not merely dimmed (D-6).
                  Always mounted so the live region exists before it changes;
                  only rendered visibly once actually zoomed, matching mockup
                  states A vs B/C. */}
              <div
                data-testid="image-viewer-zoom-level"
                aria-live="polite"
                className={cn(
                  "rounded-full bg-gallery-control/40 px-2 py-0.5 text-xs tabular-nums text-gallery-control-foreground",
                  // Visible only once it actually carries a zoom level, so the
                  // pill never paints as an empty capsule for the one frame
                  // between the zoom commit and the announcement effect.
                  announcement !== "" && scale > MIN_SCALE && canZoom ? "" : "sr-only",
                )}
              >
                {announcement}
              </div>

              <div
                ref={toolbarRef}
                data-testid="image-viewer-toolbar"
                className="pointer-events-auto flex items-center gap-2 rounded-full bg-gallery-control/40 p-1"
              >
                <button
                  type="button"
                  data-testid="image-viewer-zoom-in"
                  onClick={handleZoomIn}
                  disabled={!canZoom || atMaxScale}
                  aria-label={t("catalog.image_viewer.zoom_in")}
                  className="grid h-10 w-10 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60 disabled:opacity-45"
                >
                  <Plus className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  data-testid="image-viewer-zoom-out"
                  onClick={handleZoomOut}
                  disabled={!canZoom || atMinScale}
                  aria-label={t("catalog.image_viewer.zoom_out")}
                  className="grid h-10 w-10 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60 disabled:opacity-45"
                >
                  <Minus className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  data-testid="image-viewer-zoom-reset"
                  onClick={handleZoomReset}
                  disabled={!canZoom || atMinScale}
                  aria-label={t("catalog.image_viewer.zoom_reset")}
                  className="grid h-10 w-10 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-colors hover:bg-gallery-control/60 disabled:opacity-45"
                >
                  <Maximize2 className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>

          {showNav && (
            <div
              ref={stripRef}
              data-testid="image-viewer-strip"
              className={cn(
                "flex h-20 shrink-0 items-center gap-1.5 overflow-x-auto bg-background/70 px-3 py-2 transition-opacity duration-150",
                // Story 22.3 round-3 (Codex P2): when chrome is hidden,
                // disable hit-testing on the strip so tap-to-restore
                // falls through to the viewer root. Without
                // `pointer-events-none` the strip's lower 20px stays a
                // dead zone (still in flex layout, just transparent),
                // and the round-2 strip-touch guard would still
                // intercept touches → user couldn't restore chrome by
                // tapping the bottom area.
                chromeVisible
                  ? "opacity-100"
                  : "pointer-events-none opacity-0",
              )}
              aria-hidden={!chromeVisible}
            >
              {sources.map((s, idx) => (
                <button
                  key={`${idx}-${s.thumbUrl}`}
                  type="button"
                  data-testid="image-viewer-thumb"
                  data-thumb-idx={idx}
                  onClick={() => {
                    setActiveIdx(idx);
                    setChromeVisible(true);
                  }}
                  aria-label={t("catalog.image_viewer.thumb_label", { index: idx + 1 })}
                  aria-current={idx === activeIdx ? "true" : undefined}
                  className={cn(
                    "size-16 shrink-0 overflow-hidden rounded",
                    idx === activeIdx
                      ? "ring-2 ring-primary"
                      : "opacity-70 hover:opacity-100",
                  )}
                >
                  {renderThumbResolved({
                    src: s.thumbUrl,
                    alt: "",
                    className: "size-full object-cover",
                  })}
                </button>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
