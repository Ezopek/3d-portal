import * as Sentry from "@sentry/react";
import type { AnyRouter } from "@tanstack/react-router";

import { getAuthSnapshot } from "@/shell/AuthContext";

/**
 * Subscribe Sentry's tag scope to TanStack Router navigation events so every
 * captured event (uncaught error, manual captureException, smoke event)
 * carries the route the user was on at the moment it fired.
 *
 * Static identity tags (service.version, host.name, deployment.environment,
 * git.commit, build.time) are attached at SDK init in instrument.ts (Story
 * 2.2). This story (2.3) adds the dynamic half: route.pathname / model.id /
 * auth.is_authenticated re-emitted on every onLoad — architecture Decision G.
 *
 * The listener runs OUTSIDE React's render cycle, so it cannot use useAuth().
 * AuthContext exposes getAuthSnapshot() for that exact reason.
 *
 * Returns the unsubscribe; the caller in App.tsx intentionally discards it
 * (subscription lifetime equals app lifetime).
 */
export function attachRouterContext(router: AnyRouter): () => void {
  return router.subscribe("onLoad", (event) => {
    Sentry.setTag("route.pathname", event.toLocation.pathname);

    const match = router.state.matches.find((m) => m.routeId === "/catalog/$id");
    const params = match?.params as { id?: string } | undefined;
    // Explicit `undefined` clears the tag from the active scope (Sentry SDK
    // 8.x semantics) — without this a stale `m_142` would stick when the
    // user navigates away from /catalog/$id.
    Sentry.setTag("model.id", params?.id);

    const { isAuthenticated } = getAuthSnapshot();
    // Stringify so downstream `beforeSend` filter regex (Story 2.4) and
    // GlitchTip dashboard tag filters see a stable "true"/"false" literal.
    Sentry.setTag("auth.is_authenticated", String(isAuthenticated));
  });
}
