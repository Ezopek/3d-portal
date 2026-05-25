// Initiative 10 Story 16.3 (Architecture Decision M) — anonymous share-link
// viewer route. Anonymous visitors land here from a member-generated share
// link; the route renders a minimal model-detail view WITHOUT the standard
// AppShell chrome (no ModuleRail, no full TopBar) and WITHOUT consulting auth
// state (anonymous users must reach the view directly).
//
// NFR10-SHARE-SECURITY-1 contract:
//   - No calls to /api/auth/me (would surface anonymous user as session).
//   - No cookies on any /api/share/* fetch (handled by share-api.fetchShareView).
//   - No admin-mutating UI elements rendered.
//   - All asset URLs come from the server-side ShareModelView projection
//     (`/api/share/<token>/...`) — never the authenticated `/api/sot/...` path.

import { createFileRoute } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, Maximize2 } from "lucide-react";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { fetchShareView, type ShareModelView } from "@/lib/share-api";
import { cn } from "@/lib/utils";
// Story 22.3 (TB-037 viewer) — symmetric fullscreen image viewer mount.
// Imported via the lazy barrel so the viewer body is code-split out of the
// share route's initial chunk (which already carries the Three.js viewer
// gated by its own Suspense above) per [[feedback_lazy_import_discipline]].
// The cookie-credential boundary stays at the `renderImage` prop:
// ShareCarousel passes `AnonymousImage` so blob fetches keep
// `credentials:"omit"` (NFR10/12).
import {
  ImageFullscreenViewer,
  type ImageSource,
} from "@/modules/catalog/components/imageViewer";

import {
  acquireShareBlob,
  clearShareBlobCache,
  releaseShareBlob,
} from "./shareBlobCache";
// Use the lazy export from the viewer3d barrel so the Three.js stack stays
// code-split out of the initial app bundle. Importing the default export
// directly would defeat the dynamic import the barrel sets up and pull
// Three into every route's initial bundle (Codex Story 19.7 P2).
import { Viewer3DInline } from "@/modules/catalog/components/viewer3d";
import type { StlFile } from "@/modules/catalog/components/viewer3d/types";
// Initiative 18 Story 30.3 / FR18-CHROME-ADDITIONS-1 — share-view header
// gains three right-aligned controls (ThemeToggle + LangToggle + SignInButton)
// mirroring member TopBar order. Per [[feedback_share_view_scope_boundary]]
// amended carve-out 2026-05-25, CHROME affordances are membership-path
// completion, NOT share-view content enrichment — anonymous CONTENT below
// (carousel, STL, description, footer) stays terminus.
import { useAuth } from "@/shell/AuthContext";
import { LangToggle } from "@/shell/LangToggle";
import { ThemeToggle } from "@/shell/ThemeToggle";
import { LoadingState } from "@/ui/custom/LoadingState";

import { MemberShareView } from "./MemberShareView";
import { SignInButton } from "./SignInButton";

/**
 * Anonymous STL download button — fetches the file as a credentialless blob
 * (NFR10-SHARE-SECURITY-1) so a logged-in user viewing the share link
 * doesn't attach their portal_access cookie to the download. Plain
 * `<a href={url} download>` would send cookies because the browser cannot
 * disable credentials for navigation anchors.
 */
function AnonymousDownloadButton({
  url,
  filename,
  label,
}: {
  url: string;
  filename: string;
  label: string;
}) {
  const [loading, setLoading] = useState(false);
  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const r = await fetch(url, { credentials: "omit" });
      if (!r.ok) throw new Error(`download_${r.status}`);
      const blob = await r.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } finally {
      setLoading(false);
    }
  };
  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading}
      className="mt-3 inline-flex items-center rounded border border-border bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
    >
      {label}
    </button>
  );
}

/**
 * Anonymous image loader — fetches the asset as a credentialless blob and
 * assigns the resulting object-URL to the `<img>` src. Same-origin `<img>`
 * elements send cookies by default (crossOrigin="anonymous" only matters
 * for cross-origin requests), so without this blob round-trip a logged-in
 * user opening /share/<token> would still attach their portal_access
 * cookie to every gallery/thumbnail load (Codex P2 round-2 finding
 * 2026-05-22). NFR10-SHARE-SECURITY-1.
 */
// Blob-cache helpers live in the sibling `shareBlobCache.ts` module so this
// route file can stay focused on JSX/components (and not trip
// react-refresh/only-export-components). See that module's header comment
// for the full design rationale (NFR12 rate-limit reason the cache exists,
// Story 23.1 TB-033 P2#1/P2#2 hardening).
function AnonymousImage({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  useEffect(() => {
    // Codex 19.5 round-2 P2 — reset blob state on src change so the previous
    // image doesn't keep rendering while the new one loads (or forever if
    // the new fetch 404s / 429s). Each src starts from a clean loading state.
    setObjectUrl(null);
    let cancelled = false;
    acquireShareBlob(src)
      .then((url) => {
        if (!cancelled) setObjectUrl(url);
      })
      .catch(() => {
        // Silent fail: the empty placeholder remains visible; we don't surface
        // load errors at the per-image level for share view.
      });
    return () => {
      cancelled = true;
      releaseShareBlob(src);
    };
  }, [src]);
  if (objectUrl === null) {
    return <div className={`${className ?? ""} animate-pulse bg-muted`} aria-label={alt} />;
  }
  return <img src={objectUrl} alt={alt} className={className} />;
}

/**
 * Story 22.2 round-2 (Codex P2) — lazy-loading variant of AnonymousImage that
 * defers the share-asset fetch until the element scrolls into (or near) the
 * viewport. Wraps an IntersectionObserver around a placeholder div; only
 * mounts the real AnonymousImage once `isIntersecting` fires.
 *
 * Why: Story 22.2 round-1 made the strip fetch `?variant=thumb` and the main
 * frame fetch `?variant=gallery` — different URLs defeated the previously
 * implicit dedupe between strip[activeIdx] and main, raising eager fetches
 * from N to N+1 per N-image carousel. On shares with >60 images, the
 * (token, IP) 60 req/min cap (Init 12 Story 19.1) would trigger 429 on the
 * 61st fetch and leave a thumbnail stuck on the loading placeholder.
 *
 * Lazy-load reduces eager strip fetches to ~visible-window (typically 5-7
 * thumbs at first paint instead of all N). The `rootMargin: "200px"` pre-warm
 * keeps the next-just-off-screen thumbs loading early enough to avoid a
 * visible flash during scroll. Falls back to immediate mount in JSDOM /
 * environments without IntersectionObserver (defensive).
 */
function LazyAnonymousImage({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const [shouldFetch, setShouldFetch] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    // Defensive: JSDOM doesn't ship IntersectionObserver. Fall back to
    // immediate eager fetch so vitest tests keep matching the
    // AnonymousImage behaviour they previously asserted.
    if (typeof window === "undefined" || typeof window.IntersectionObserver === "undefined") {
      setShouldFetch(true);
      return undefined;
    }
    const node = sentinelRef.current;
    if (node === null) {
      setShouldFetch(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShouldFetch(true);
            observer.disconnect();
            return;
          }
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  if (!shouldFetch) {
    return (
      <div
        ref={sentinelRef}
        className={`${className ?? ""} bg-muted/30`}
        aria-label={alt}
      />
    );
  }
  return <AnonymousImage src={src} alt={alt} className={className} />;
}

/**
 * Initiative 12 Story 19.5 — carousel for the anonymous share view, parity
 * with `ModelGallery` on the authenticated catalog detail page. One image
 * visible at a time + thumbnail strip + prev/next chevrons. Each frame goes
 * through `AnonymousImage` so the credentialless contract (NFR10/12) holds:
 * no same-origin cookies on /api/share/* asset fetches.
 *
 * Image source order:
 *  1. `thumbnailUrl` (chosen catalog thumbnail) first — matches what the
 *     recipient saw in the share-link preview.
 *  2. `imageUrls` (admin-ordered gallery) — preserves admin photo-order.
 * Duplicates of the thumbnail in imageUrls are filtered out to avoid
 * showing the same image twice.
 */
function ShareCarousel({
  thumbnailUrl,
  imageUrls,
  altLabel,
}: {
  thumbnailUrl: string | null;
  imageUrls: readonly string[];
  altLabel: string;
}) {
  const { t } = useTranslation();
  // Memoise `ordered` so dependent useMemo (viewerSources) keeps a stable
  // reference across renders — required for rules-of-hooks order + the
  // exhaustive-deps lint when feeding the array as a hook dep.
  const ordered = useMemo<string[]>(() => {
    const out: string[] = [];
    if (thumbnailUrl !== null) out.push(thumbnailUrl);
    for (const url of imageUrls) {
      if (url !== thumbnailUrl) out.push(url);
    }
    return out;
  }, [thumbnailUrl, imageUrls]);
  const [activeIdx, setActiveIdx] = useState(0);
  // Story 22.3 — fullscreen viewer mount state. Hooks placed above the
  // early-return guards (rules-of-hooks). The viewer pulls `?variant=full`
  // (original-resolution blob, falling through to the un-varianted path
  // when the backend's variant resolver has no `.full.webp` sibling) and
  // reuses `AnonymousImage` so the credentialless contract (NFR10/12)
  // holds on every blob fetch.
  const [fullscreenOpen, setFullscreenOpen] = useState(false);
  const viewerSources = useMemo<ImageSource[]>(
    () =>
      ordered.map((url, idx) => ({
        fullUrl: `${url}?variant=full`,
        thumbUrl: `${url}?variant=thumb`,
        alt: `${altLabel} ${idx + 1}`,
      })),
    [ordered, altLabel],
  );

  if (ordered.length === 0) {
    return null;
  }

  const activeUrl = ordered[activeIdx] ?? ordered[0];
  if (activeUrl === undefined) {
    return null;
  }
  const showNav = ordered.length > 1;
  const onPrev = () => setActiveIdx((i) => (i === 0 ? ordered.length - 1 : i - 1));
  const onNext = () => setActiveIdx((i) => (i + 1) % ordered.length);

  // Story 22.2 (FR16-CAROUSEL-TIER-1) — main frame consumes the gallery
  // tier (~150-500 KB) instead of the original (4-8 MB). Story 22.1
  // round-2 (commit 05ad8f0) extended the anonymous /api/share/<token>/
  // files/<fid>/content endpoint to accept `?variant=gallery` and serve
  // the `.gallery.webp` sibling, falling back silently to the original
  // when the sibling is missing (backward-compatible during rollout
  // before the .190 backfill completes). AnonymousImage's cache key is
  // the full URL, so each variant maps to its own cache bucket — no
  // invalidation needed.
  const mainUrl = `${activeUrl}?variant=gallery`;

  return (
    <section className="space-y-2" aria-label={t("share.view.carousel_label")}>
      <div className="group relative">
        <button
          type="button"
          data-testid="share-fullscreen-trigger"
          onClick={() => setFullscreenOpen(true)}
          aria-label={t("catalog.image_viewer.trigger_label")}
          className="block w-full cursor-zoom-in"
        >
          <AnonymousImage
            src={mainUrl}
            alt={altLabel}
            className="aspect-[4/3] w-full rounded border border-border object-contain bg-muted/30"
          />
        </button>
        <button
          type="button"
          data-testid="share-fullscreen-icon"
          onClick={() => setFullscreenOpen(true)}
          aria-label={t("catalog.image_viewer.trigger_label")}
          title={t("catalog.image_viewer.trigger_tooltip")}
          className="absolute right-2 top-2 grid h-9 w-9 place-items-center rounded-full bg-gallery-control/40 text-gallery-control-foreground transition-opacity hover:bg-gallery-control/60 focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
        {showNav && (
          <>
            <button
              type="button"
              onClick={onPrev}
              aria-label={t("share.view.carousel_prev")}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/80 p-1.5 text-foreground shadow ring-1 ring-border backdrop-blur hover:bg-background"
            >
              <ChevronLeft className="size-5" />
            </button>
            <button
              type="button"
              onClick={onNext}
              aria-label={t("share.view.carousel_next")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/80 p-1.5 text-foreground shadow ring-1 ring-border backdrop-blur hover:bg-background"
            >
              <ChevronRight className="size-5" />
            </button>
          </>
        )}
      </div>
      {showNav && (
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {ordered.map((url, idx) => (
            <button
              key={url}
              type="button"
              onClick={() => setActiveIdx(idx)}
              aria-label={t("share.view.carousel_thumb_label", { index: idx + 1 })}
              aria-current={idx === activeIdx ? "true" : undefined}
              className={cn(
                "size-14 shrink-0 overflow-hidden rounded border-2",
                idx === activeIdx ? "border-primary" : "border-transparent hover:border-border",
              )}
            >
              <LazyAnonymousImage
                src={`${url}?variant=thumb`}
                alt=""
                className="size-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
      {fullscreenOpen && (
        <Suspense fallback={null}>
          <ImageFullscreenViewer
            sources={viewerSources}
            initialIndex={activeIdx}
            onClose={() => setFullscreenOpen(false)}
            renderImage={AnonymousImage}
            // Story 22.3 round-2 (Codex P1): use the lazy variant for
            // the strip thumbs so the viewer doesn't bypass the route's
            // existing LazyAnonymousImage mitigation (Story 22.2
            // round-2). Without this, opening the viewer on a
            // /share/<token> with many photos would burst-fetch every
            // thumbnail at once and risk crossing the 60 req/min
            // (token, IP) cap from Init 12 Story 19.1.
            renderThumb={LazyAnonymousImage}
          />
        </Suspense>
      )}
    </section>
  );
}

/**
 * Construct a Viewer3DInline-compatible StlFile from the share resolve
 * payload. Sets srcOverride to the share-scoped STL URL (with ?download=1
 * stripped so the viewer fetches inline content) so useStlGeometry routes
 * through credentials:"omit". modelId/fileId carry the share-view's model
 * id + a placeholder file id; they're only used as skip-gate semantics
 * when srcOverride is null (which it isn't here), so the placeholder is
 * benign. size set to 0 — share resolve doesn't carry STL byte size; the
 * large-mesh confirm gate falls through (acceptable for recipients who
 * explicitly opened a share link).
 */
function shareStlFile(data: ShareModelView, title: string): StlFile {
  const stlUrl = data.stl_url ?? "";
  const cleanedSrc = stlUrl.endsWith("?download=1") ? stlUrl.slice(0, -"?download=1".length) : stlUrl;
  return {
    id: "share-stl",
    modelId: data.id,
    name: `${title}.stl`,
    // size from ShareModelView.stl_size_bytes when present so the large-STL
    // confirm gate in Viewer3DInline (needsConfirmForSize) still fires for
    // anonymous recipients on shares >50 MB. Falls back to 0 only when the
    // backend returns null (unknown size) — in which case the gate skips
    // and the viewer loads the STL eagerly. Story 19.7 round-2 P2 fix.
    size: data.stl_size_bytes ?? 0,
    srcOverride: cleanedSrc,
  };
}

export function AnonymousShareView({ token }: { token: string }) {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<ShareModelView | null>(null);
  const [error, setError] = useState<"not_found" | "fetch_failed" | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchShareView(token)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setLoading(false);
        setError(err.message === "share_view_404" ? "not_found" : "fetch_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error === "not_found" || (error === null && data === null)) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md text-center">
          <h1 className="text-xl font-semibold">{t("share.view.not_found_title")}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("share.view.not_found_description")}
          </p>
        </div>
      </div>
    );
  }

  if (error === "fetch_failed" || data === null) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md text-center">
          <h1 className="text-xl font-semibold">{t("share.view.error_title")}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("share.view.error_description")}
          </p>
        </div>
      </div>
    );
  }

  const preferPl = i18n.language?.toLowerCase().startsWith("pl");
  const title =
    preferPl && data.name_pl !== null && data.name_pl !== "" ? data.name_pl : data.name_en;
  const notes =
    preferPl && data.notes_pl !== ""
      ? data.notes_pl
      : data.notes_en !== ""
        ? data.notes_en
        : data.notes_pl;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{t("share.view.brand")}</span>
          <span className="flex-1 text-xs text-muted-foreground">
            {t("share.view.banner_anonymous")}
          </span>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <LangToggle />
            <SignInButton token={token} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-4 p-4">
        <section className="space-y-2">
          <div className="text-xs text-muted-foreground">{data.category}</div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          {data.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {data.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-muted px-1.5 py-0.5 text-xs text-chip-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </section>

        {/* Initiative 12 Story 19.5 (FR12-SHARE-CAROUSEL-1) — carousel parity
            with authenticated catalog detail. ShareCarousel renders one image
            at a time with prev/next chevron navigation + thumbnail strip
            below, mirroring ModelGallery's UX. AnonymousImage continues to
            route every fetch through credentials:"omit" + blob (NFR10/12
            credentialless contract). */}
        <ShareCarousel
          thumbnailUrl={data.thumbnail_url}
          imageUrls={data.images}
          altLabel={title}
        />

        {data.has_3d && data.stl_url !== null && (
          <section className="space-y-3 rounded border border-border bg-card p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("share.view.stl_label")}
            </h2>
            {/* Initiative 12 Story 19.7 (FR12-SHARE-3D-VIEWER-1) — embedded
                inline 3D viewer using Init 13 Story 20.3 srcOverride hook.
                The viewer fetches the STL via fetch(url, credentials:"omit")
                so same-origin cookies do NOT attach when a logged-in user
                opens the share link. data.stl_url already has ?download=1
                appended for the download anchor below; strip it for the
                viewer fetch so the server returns inline content-disposition.
                onExpand omitted — no modal host on share view (would need
                operator-aligned scope to add).

                Viewer3DInline is lazy() — wrap in Suspense to defer the
                Three.js chunk until the viewer actually mounts. */}
            <Suspense
              fallback={
                <div className="grid aspect-square w-full place-items-center rounded border border-border bg-muted/30 text-xs text-muted-foreground md:aspect-auto md:min-h-[280px]">
                  {t("share.view.stl_viewer_loading")}
                </div>
              }
            >
              <Viewer3DInline file={shareStlFile(data, title)} />
            </Suspense>
            <p className="text-sm text-muted-foreground">
              {t("share.view.stl_description")}
            </p>
            <AnonymousDownloadButton
              url={data.stl_url}
              filename={`${title}.stl`}
              label={t("share.view.download_stl")}
            />
          </section>
        )}

        {notes !== "" && (
          <section className="rounded border border-border bg-card p-4">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("share.view.description_label")}
            </h2>
            <div className="whitespace-pre-wrap text-sm text-card-foreground">{notes}</div>
          </section>
        )}

        <footer className="pt-4 text-center text-xs text-muted-foreground">
          {t("share.view.footer_anonymous_notice")}
        </footer>
      </main>
    </div>
  );
}

function ShareTokenRoute() {
  const { token } = Route.useParams();
  const auth = useAuth();
  // Story 23.1 (TB-033 P2#2) — Decision X.1 policy A: page-mount-scoped
  // blob-cache invalidation. On route unmount, revoke every cached object
  // URL and clear all three maps so a subsequent re-mount of /share/<token>
  // (same or different token) starts from a clean slate. Without this, a
  // recipient who keeps the tab open across a model-owner share revocation
  // would continue seeing cached photos until manual refresh. After this
  // cleanup, navigating away + back triggers fresh fetches that will
  // surface the now-revoked token's 404/403. Full rationale lives in
  // `shareBlobCache.clearShareBlobCache`. The cleanup applies to both
  // anonymous + member branches — the member branch may not use
  // AnonymousImage, but the cleanup is benign in that case (empty maps).
  useEffect(() => {
    return () => {
      clearShareBlobCache();
    };
  }, []);

  // Initiative 18 Story 30.2 (Decision AB) — split on useAuth() result.
  // While auth resolves, render a skeleton placeholder rather than picking
  // a branch prematurely (the alternative would flash anonymous content
  // for ~50ms then swap to member view when /auth/me resolves).
  if (auth.isLoading) {
    return <LoadingState variant="skeleton-detail" />;
  }
  if (auth.isAuthenticated) {
    return <MemberShareView token={token} />;
  }
  return <AnonymousShareView token={token} />;
}

export const Route = createFileRoute("/share/$token")({
  // Initiative 10 Story 16.3 — NO AuthGate. AppShell.AuthGate would force a
  // /login redirect for anonymous visitors; this route is intentionally
  // bypassed via the path-prefix `/share/` check in AppShell.tsx
  // `_PUBLIC_PATHS`. Verify the prefix matches at integration time.
  component: ShareTokenRoute,
});

// Test-only handle. Production callers MUST NOT reach into this — the
// `AnonymousImage` component is module-private. Exposed for Story 23.1
// StrictMode test (TB-033 AC4 mounts AnonymousImage directly to exercise
// the acquire/release cycle without TanStack Router scaffolding).
// Blob-cache state-inspection lives in `shareBlobCache.ts`.
//
// eslint-disable-next-line react-refresh/only-export-components
export const __test_AnonymousImage = AnonymousImage;
