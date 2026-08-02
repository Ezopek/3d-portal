import { ApiError } from "./api";
import { refreshAccessToken } from "./refresh";

/**
 * Credentialed BINARY fetch for `/api/*` assets.
 *
 * `api<T>()` is a JSON contract at its exit (`return (await response.json())`),
 * so it cannot serve image/model bytes. This is the explicit binary
 * response-mode sibling: same credential rules, same CSRF header, same 401
 * `detail` -> refresh -> retry-ONCE contract, same `ApiError` surface,
 * different response mode.
 *
 * Why it exists: a native `<img src="/api/models/.../content">` load carries
 * the cookie but is invisible to that retry path, so once `portal_access`
 * (10 min max-age) expires under a long-lived surface — the catalog lightbox —
 * every photo 401s with no way back short of a page reload. Measured in
 * production 2026-08-02: ten `?variant=full` 401s at 19:36:41-19:36:55 while
 * the refresh session was still valid.
 *
 * `credentials: "include"` is deliberate and is the OPPOSITE of the
 * `/share/<token>` contract (`credentials: "omit"`, NFR10-SHARE-SECURITY-1),
 * which is why the same-origin `/api/` prefix is enforced STRUCTURALLY below
 * rather than by convention: this helper must be impossible to point at a
 * share asset (or an off-origin URL) by a later refactor.
 *
 * `signal` lets the caller abort a recovery it no longer needs — a lightbox
 * user who arrows past a photo should not keep pulling a 4-8 MB original over
 * mobile data.
 */
export async function fetchApiBlob(url: string, signal?: AbortSignal): Promise<Blob> {
  if (!url.startsWith("/api/") || url.startsWith("/api/share/")) {
    throw new ApiError(0, null, `refusing to send credentials to ${url}`);
  }
  const first = await request(url, signal);
  // Only the two documented refresh candidates. Widening this set is an auth
  // decision, not a convenience: the refresh token ROTATES on every use and
  // replaying a rotated one invalidates the whole session family, so a blind
  // refresh on any 401 (or on any image error) is a live footgun. This mirrors
  // `api.ts` exactly; the two must not drift apart.
  if (first.status === 401 && (await isRefreshable(first))) {
    // Callers that overlap the in-flight window share ONE rotation (the
    // `refreshAccessToken` singleton). Callers that arrive after it settled
    // rotate again — which is safe (a rotation, not a replay) and normally
    // does not happen, because once the first refresh lands the cookie is
    // fresh and later probes get 200 instead of 401.
    if (await refreshAccessToken()) {
      return toBlob(await request(url, signal), url);
    }
  }
  return toBlob(first, url);
}

async function request(url: string, signal?: AbortSignal): Promise<Response> {
  try {
    return await fetch(url, {
      credentials: "include",
      headers: { "X-Portal-Client": "web" },
      ...(signal !== undefined ? { signal } : {}),
    });
  } catch (cause) {
    // Offline / DNS / aborted transport. Surfaced as `ApiError` so callers have
    // one error shape to handle, same as the JSON wrapper.
    throw new ApiError(0, null, `network error loading ${url}: ${String(cause)}`);
  }
}

async function isRefreshable(response: Response): Promise<boolean> {
  const body = await response.clone().json().catch(() => ({}));
  const detail = (body as { detail?: string })?.detail;
  return detail === "access_expired" || detail === "missing_access";
}

async function toBlob(response: Response, url: string): Promise<Blob> {
  if (!response.ok) {
    // Carry the parsed body, not `null`: `instrument-filters.ts` suppresses
    // GlitchTip noise by reading `ApiError.body.detail`, and the admin surfaces
    // read it for user-facing copy. An `ApiError` without a body is a different
    // error surface than `api()`'s, whatever the status code says.
    const body = await response.clone().json().catch(() => null);
    throw new ApiError(response.status, body, `${response.status} loading ${url}`);
  }
  try {
    return await response.blob();
  } catch (cause) {
    // The body can fail AFTER a 200 header — a dropped connection mid-transfer
    // on a multi-MB original is the realistic case on mobile.
    throw new ApiError(0, null, `body read failed for ${url}: ${String(cause)}`);
  }
}
