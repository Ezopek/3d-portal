import { useEffect, useState } from "react";

import { fetchApiBlob } from "@/lib/api-blob";

/**
 * Authenticated `<img>` that survives an access-session expiry.
 *
 * `portal_access` has a 10-minute max-age; the fullscreen lightbox stays open
 * far longer. A native `<img>` load carries the cookie but is invisible to the
 * `api()` wrapper's `401 -> refreshAccessToken() -> retry` path, so once the
 * cookie expires every photo fails permanently (production, 2026-08-02: ten
 * `?variant=full` 401s at 19:36:41-19:36:55 while the refresh session was
 * still valid).
 *
 * The recovery is ERROR-DRIVEN, not blob-first, and that is the load-bearing
 * design choice:
 *   - the happy path stays a plain native `<img>`, so progressive decoding of
 *     4-8 MB originals on a phone is preserved, the HTTP cache still serves
 *     re-visits, and nothing about the viewer's readiness probe changes. A
 *     blob-first renderer would move `/catalog` onto the viewer's
 *     never-mounted-`<img>` branch and re-arm the 15 s readiness watchdog that
 *     ruling DN-2 deliberately narrowed away — announcing a still-downloading
 *     photo as a terminal failure;
 *   - an `<img>` `error` event carries no status, and refresh tokens ROTATE on
 *     every use (reuse invalidates the whole session family), so we must not
 *     refresh on a bare image error. One credentialed fetch of the same URL is
 *     what turns "the image broke" into "the image broke with 401
 *     access_expired".
 *
 * Bounded by construction: at most one recovery per `src` (the effect's deps
 * cannot change again within a `src`), which is at most one refresh and one
 * retry. On terminal failure the failed native `<img>` stays mounted, so the
 * viewer's own inline error state — already raised by the same `error` event —
 * stands unchanged.
 *
 * NOT for `/share/<token>`: that surface must stay credentialless
 * (`credentials: "omit"`, NFR10-SHARE-SECURITY-1) and keeps using
 * `AnonymousImage` + `shareBlobCache`.
 */
export function AuthenticatedImage({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  /** The `src` whose NATIVE load failed — arms recovery for that src only. */
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const [recovered, setRecovered] = useState<{ src: string; url: string } | null>(null);

  // Both pieces of state are compared against the CURRENT src rather than
  // reset from an effect: a stale entry must never render the previous photo's
  // (already revoked) object URL for one commit.
  const armed = failedSrc === src;
  const objectUrl = recovered?.src === src ? recovered.url : null;

  useEffect(() => {
    if (!armed) return undefined;
    let cancelled = false;
    let created: string | null = null;
    // Abort rather than merely ignore: a user arrowing past a photo should not
    // keep pulling a 4-8 MB original over mobile data to then throw it away.
    const controller = new AbortController();
    fetchApiBlob(src, controller.signal)
      .then((blob) => {
        // A 200 is not proof of an image: a misrouted proxy, a maintenance page
        // or an HTML login redirect all arrive as a perfectly good `Blob`.
        // Swapping one in would replace a diagnosable URL with an object URL
        // guaranteed to fail decode — and that failure is terminal by design.
        if (!blob.type.startsWith("image/")) {
          throw new Error(`recovered payload is not an image: ${blob.type || "unknown"}`);
        }
        const url = URL.createObjectURL(blob);
        if (cancelled) {
          // Unmounted / navigated away while the retry was in flight. Revoke
          // here rather than in the cleanup that already ran, and do not touch
          // state.
          URL.revokeObjectURL(url);
          return;
        }
        created = url;
        setRecovered({ src, url });
      })
      .catch(() => {
        // Terminal: dead refresh session, 404, offline, aborted, non-image
        // payload. The failed `<img>` is still mounted and the viewer has
        // already reported the error.
      });
    return () => {
      cancelled = true;
      controller.abort();
      // Disarm so returning to this photo later (token now fresh) loads
      // natively again instead of replaying a fetch. FUNCTIONAL update on
      // purpose: if a new src has already armed itself before React flushed
      // this cleanup, a bare `setFailedSrc(null)` would silently disarm THAT
      // recovery, and no second `error` event would ever arrive to re-arm it.
      setFailedSrc((current) => (current === src ? null : current));
      if (created !== null) {
        URL.revokeObjectURL(created);
        setRecovered((current) => (current?.url === created ? null : current));
      }
    };
  }, [armed, src]);

  return (
    <img
      data-testid="authed-image"
      src={objectUrl ?? src}
      alt={alt}
      className={className}
      onError={() => {
        // Only the native load arms recovery. An object URL that fails to
        // decode must not restart the chain.
        if (objectUrl === null) setFailedSrc(src);
      }}
    />
  );
}
