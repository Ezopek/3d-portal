import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { ApiError } from "@/lib/api";
import { CatalogDetailRender } from "@/modules/catalog/routes/CatalogDetail";
import { EmptyState } from "@/ui/custom/EmptyState";
import { LoadingState } from "@/ui/custom/LoadingState";

import { AnonymousShareView } from "./$token";
import { ShareMemberContextInfoBar } from "./ShareMemberContextInfoBar";
import { useShareModelProbe } from "./useShareModelProbe";
import { useShareResolve } from "./useShareResolve";

// Initiative 18 Story 30.2 (FR18-MEMBER-SHARE-VIEW-1) — B5 enrich-in-place
// at /share/<token>. Renders the canonical catalog detail UI for the model
// the share token resolves to, plus a dismissible info-bar pointing at the
// canonical /catalog/$id URL. URL stays /share/<token> (brainstorm rα-1
// mitigation by design — bookmark stability, back-button stability).
//
// Two-phase fetch: first resolve the token → model_id (Story 30.1
// endpoint); then fetch the model detail (existing useModel). Either
// fetch can return 404 (token revoked/expired/soft-deleted-model OR
// model deleted/soft-deleted between resolve + detail) — in both cases
// fall through to AnonymousShareView so the recipient sees the existing
// "share link expired" copy.
//
// Story 30.2 round-2+3+4+5 (Codex P2 chain) — the second-phase model-
// detail fetch is explicitly status-checked here (rather than letting
// CatalogDetailBody's internal generic-error UI render) so the post-
// resolve 404 race (model soft-deleted between the resolve and the
// detail fetch) surfaces the same share-expired UX as the resolve-side
// 404. The probe result IS the render source-of-truth (passed to
// `CatalogDetailRender`) so validation + rendering stay atomic — no
// secondary CatalogDetailBody fetch that could race against the probe.
//
// Round-5 design — `useShareModelProbe` uses the CANONICAL
// `['sot', 'models', id]` queryKey (NOT a private share key) so admin
// mutations (`useReplaceTags`, `useUpdateModel`, file uploads/deletes,
// etc.) that invalidate the canonical cache also re-trigger the
// share-view probe. To keep freshness despite the shared cache, the
// probe overrides observer options: staleTime 0 + refetchOnMount
// "always" + retry false, so every share-page mount issues a fresh
// GET regardless of cached state. Trade-off accepted: React Query's
// stale-while-revalidate may render the cached value for one frame
// during the in-flight refetch on warm-cache visits — bounded flash,
// rare in practice (requires same-tab visit to /catalog/$id within
// the last 30s AND deletion between the visits).
//
// Other failure modes:
//   - 401 (defensive, shouldn't happen — caller is authenticated): same
//     fallback. AppShell + AuthContext already gate the parent route on
//     auth.isAuthenticated, so this branch is belt-and-suspenders.
//   - 5xx / network: standard EmptyState with retry affordance.
export function MemberShareView({ token }: { token: string }) {
  const {
    data: resolveData,
    isLoading: resolveLoading,
    isError: resolveError,
    error: resolveErr,
    refetch: resolveRefetch,
  } = useShareResolve(token);

  // Probe the model-detail endpoint via a share-specific queryKey (NOT
  // the catalog cache — see round-3 rationale above). useShareModelProbe
  // disables itself when modelId is empty so the resolve-pending window
  // doesn't fire a spurious GET /api/models/.
  //
  // Round-4 (Codex P2 follow-up): we now USE the probe's data directly
  // as the render source-of-truth (passing to CatalogDetailRender). This
  // makes validation + rendering atomic — there is no second
  // CatalogDetailBody fetch that could race with a between-requests
  // delete and surface stale or generic-network UX.
  const modelId = resolveData?.model_id;
  const {
    data: modelData,
    isLoading: modelLoading,
    isError: modelError,
    error: modelErr,
    refetch: modelRefetch,
  } = useShareModelProbe(modelId ?? "");

  // Round-6 (Codex P2 follow-up) — the round-5 switch to the canonical
  // queryKey means a successful share visit seeds the long-lived
  // ['sot', 'models', id] cache that `/catalog/$id` reads. If the
  // recipient navigates to /catalog/<id> within the canonical 30s
  // staleTime, they'd see the share-snapshot rather than a fresh fetch
  // (and a 404/500 from the probe would also linger). Clear the
  // canonical entry on share-route unmount — mirrors the existing
  // `clearShareBlobCache()` page-mount invalidation pattern in
  // $token.tsx (Story 23.1 Decision X.1 policy A).
  const qc = useQueryClient();
  useEffect(() => {
    return () => {
      if (modelId) {
        qc.removeQueries({ queryKey: ["sot", "models", modelId] });
      }
    };
  }, [modelId, qc]);

  if (resolveLoading) {
    return <LoadingState variant="skeleton-detail" />;
  }

  if (resolveError) {
    const status = resolveErr instanceof ApiError ? resolveErr.status : 0;
    if (status === 404 || status === 401) {
      return <AnonymousShareView token={token} />;
    }
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{ labelKey: "common.retry", onClick: () => void resolveRefetch() }}
      />
    );
  }

  if (resolveData === undefined || modelId === undefined) {
    // Defensive — should not reach (covered by resolveLoading + resolveError).
    return <LoadingState variant="skeleton-detail" />;
  }

  if (modelLoading) {
    return <LoadingState variant="skeleton-detail" />;
  }

  if (modelError) {
    const status = modelErr instanceof ApiError ? modelErr.status : 0;
    if (status === 404) {
      // Race: resolve returned 200 with model_id, but the model was
      // soft-deleted/hard-deleted between resolve and detail fetch.
      // Surface the same share-expired UX as a resolve-side 404 — the
      // recipient should NOT see a generic "Network error / Retry" button
      // for a share link that's effectively dead.
      return <AnonymousShareView token={token} />;
    }
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{ labelKey: "common.retry", onClick: () => void modelRefetch() }}
      />
    );
  }

  if (modelData === undefined) {
    // Defensive — should not reach (covered by modelLoading + modelError).
    return <LoadingState variant="skeleton-detail" />;
  }

  return (
    <div className="space-y-4 px-4 pt-4">
      <ShareMemberContextInfoBar modelId={modelId} />
      <CatalogDetailRender detail={modelData} />
    </div>
  );
}
