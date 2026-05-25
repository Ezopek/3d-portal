import { ApiError } from "@/lib/api";
import { useModel } from "@/modules/catalog/hooks/useModel";
import { CatalogDetailBody } from "@/modules/catalog/routes/CatalogDetail";
import { EmptyState } from "@/ui/custom/EmptyState";
import { LoadingState } from "@/ui/custom/LoadingState";

import { AnonymousShareView } from "./$token";
import { ShareMemberContextInfoBar } from "./ShareMemberContextInfoBar";
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
// Story 30.2 round-2 (Codex P2) — the second-phase model-detail fetch is
// explicitly status-checked here (rather than letting CatalogDetailBody's
// internal generic-error UI render) so the post-resolve 404 race
// (CatalogDetailBody's /api/models/:id returns 404 because the model
// was soft-deleted between the resolve and the detail fetch) surfaces
// the same share-expired UX as the resolve-side 404. Without this guard
// the race-window-deleted model would surface a generic "errors.network"
// retry button, which is the wrong copy for a share-context recipient.
// React Query dedupes by queryKey — CatalogDetailBody's useModel(id)
// shares the same cache as this probing call, so no double network round.
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

  // Probe the model-detail endpoint shape; same queryKey as CatalogDetailBody
  // so React Query dedupes the network round. Gated on `enabled` so the
  // network call only fires once resolve hands us a model_id (avoids a
  // spurious GET /api/models/ during the resolve-pending window).
  const modelId = resolveData?.model_id;
  const {
    isLoading: modelLoading,
    isError: modelError,
    error: modelErr,
    refetch: modelRefetch,
  } = useModel(modelId ?? "", { enabled: modelId !== undefined });

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

  return (
    <div className="space-y-4 px-4 pt-4">
      <ShareMemberContextInfoBar modelId={modelId} />
      <CatalogDetailBody id={modelId} />
    </div>
  );
}
