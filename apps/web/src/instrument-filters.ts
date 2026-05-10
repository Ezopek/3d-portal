import type { ErrorEvent, EventHint } from "@sentry/react";

import { ApiError } from "@/lib/api";

/**
 * Empirical noise ruleset paste-imported from Story 2.1's discovery output:
 * `_bmad-output/implementation-artifacts/glitchtip-discovery-2026-05-09.md`.
 *
 * The 30-day GlitchTip sample on 2026-05-09 contained 21 issues / 27 events,
 * 100% synthetic/test/operator-driven (verify-symbolication smoke events,
 * sentry-test endpoint, phase-0/3/4 manual verification, backend
 * FileNotFoundError on test routes). Empirical additions: 0. Floor patterns
 * enacted as mandated by FR5 (extension URLs) + FR6 (noise titles).
 *
 * Re-run Story 2.1's discovery 30 days post-organic-traffic activation;
 * replace the array bodies with the new dated discovery output. Do NOT
 * hand-edit these arrays without a corresponding discovery refresh — the
 * empirical floor must trace back to observed reality (NFR-I3).
 */
export const denyUrls: RegExp[] = [
  // --- floor: anticipated minimums (FR5) ---
  /^chrome-extension:\/\//,
  /^moz-extension:\/\//,
  /^safari-web-extension:\/\//,
  // --- empirical additions ---
  // (none: 30-day sample contained zero browser-extension URLs in `request.url`.)
];

export const ignoreErrors: RegExp[] = [
  // --- floor: anticipated minimums (FR6) ---
  /ResizeObserver loop/,
  /Non-Error promise rejection captured/,
  // --- empirical additions ---
  // (none: 30-day sample contained zero noise-title patterns; the entire
  //  sample is operator-driven test/synthetic/smoke events. Filtering
  //  smoke events would defeat verify-symbolication's purpose.)
];

/**
 * `Sentry.init` `beforeSend` callback (architecture Decision H, AR6). Five
 * sequential `if` branches in fixed order with separate early `return null`:
 *
 *   1. denyUrls regex match against `event.request?.url`           (FR5)
 *   2. ignoreErrors regex match against `exception.values[0].value` (FR6)
 *   3. `!navigator.onLine`                                          (FR7)
 *   4. `hint.originalException instanceof ApiError && body.detail === "access_expired"` (FR7)
 *   5. Pass-through (return event unchanged).
 *
 * Cheapest exits first. Order is non-negotiable — codified in
 * `instrument-filters.test.ts` test names.
 */
export function applyBeforeSendFilters(
  event: ErrorEvent,
  hint: EventHint,
): ErrorEvent | null {
  // 1. denyUrls (FR5) — page URL the user was on, NOT script URL.
  const url = event.request?.url ?? "";
  for (const pattern of denyUrls) {
    if (pattern.test(url)) return null;
  }
  // 2. ignoreErrors (FR6) — first exception's `.value` field per Decision H.
  const value = event.exception?.values?.[0]?.value ?? "";
  for (const pattern of ignoreErrors) {
    if (pattern.test(value)) return null;
  }
  // 3. Offline (FR7) — typeof guard for SSR/test contexts without DOM.
  if (typeof navigator !== "undefined" && !navigator.onLine) return null;
  // 4. ApiError access_expired (FR7) — refresh-flow noise that escaped the
  //    silent-refresh retry in api.ts:28-37 (rare; belt-and-suspenders).
  const orig = hint.originalException;
  if (
    orig instanceof ApiError &&
    (orig.body as { detail?: string } | null)?.detail === "access_expired"
  ) {
    return null;
  }
  // 5. Pass-through.
  return event;
}
