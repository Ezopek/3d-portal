import { ApiError } from "@/lib/api";
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
// Failure modes:
//   - 404 (token invalid/expired/revoked/soft-deleted-model): fall through
//     to AnonymousShareView so the recipient sees the existing "share link
//     expired" copy instead of a generic error page.
//   - 401 (defensive, shouldn't happen — caller is authenticated): same
//     fallback. AppShell + AuthContext already gate the parent route on
//     auth.isAuthenticated, so this branch is belt-and-suspenders.
//   - 5xx / network: standard EmptyState with retry affordance.
export function MemberShareView({ token }: { token: string }) {
  const { data, isLoading, isError, error, refetch } = useShareResolve(token);

  if (isLoading) {
    return <LoadingState variant="skeleton-detail" />;
  }

  if (isError) {
    const status = error instanceof ApiError ? error.status : 0;
    if (status === 404 || status === 401) {
      return <AnonymousShareView token={token} />;
    }
    return (
      <EmptyState
        messageKey="errors.network"
        tone="error"
        action={{ labelKey: "common.retry", onClick: () => void refetch() }}
      />
    );
  }

  if (data === undefined) {
    // Defensive — should not reach (covered by isLoading + isError above).
    return <LoadingState variant="skeleton-detail" />;
  }

  return (
    <div className="space-y-4 px-4 pt-4">
      <ShareMemberContextInfoBar modelId={data.model_id} />
      <CatalogDetailBody id={data.model_id} />
    </div>
  );
}
