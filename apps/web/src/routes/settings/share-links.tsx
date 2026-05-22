// Initiative 10 Story 16.3 — "My share links" settings page.
//
// Lists active share tokens the current user has minted (filtered server-
// side by GET /api/me/share-links) and lets them revoke individual tokens
// (DELETE /api/me/share-links/{token}). Used to provide self-service
// revocation without round-tripping through the admin panel.

import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { listMyShareLinks, revokeMyShareLink, type ShareToken } from "@/lib/share-api";
import { Button } from "@/ui/button";

const QUERY_KEY = ["share", "my-links"] as const;

function MyShareLinksPage() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();

  const query = useQuery<ShareToken[]>({
    queryKey: QUERY_KEY,
    queryFn: listMyShareLinks,
    staleTime: 60_000,
  });

  const revoke = useMutation({
    mutationFn: (token: string) => revokeMyShareLink(token),
    onSuccess: () => {
      toast.success(t("settings.share_links.revoked"));
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
    onError: () => {
      toast.error(t("settings.share_links.revoke_failed"));
    },
  });

  const formatExpiresAt = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <header className="space-y-2 pb-2">
        <h1 className="text-xl font-semibold">{t("settings.share_links.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("settings.share_links.description")}
        </p>
      </header>

      {query.isLoading && (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      )}

      {query.isError && (
        <p className="text-sm text-destructive">
          {t("settings.share_links.load_failed")}
        </p>
      )}

      {query.data !== undefined && query.data.length === 0 && (
        <p className="text-sm text-muted-foreground">{t("settings.share_links.empty")}</p>
      )}

      {query.data !== undefined && query.data.length > 0 && (
        <ul className="divide-y divide-border rounded border border-border">
          {query.data.map((tok) => (
            <li key={tok.token} className="flex items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1 space-y-1">
                <div className="truncate text-sm font-mono">{tok.token}</div>
                <div className="text-xs text-muted-foreground">
                  {t("settings.share_links.model_id_label")}{" "}
                  <span className="font-mono">{tok.model_id}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {t("settings.share_links.expires_at_label")}{" "}
                  {formatExpiresAt(tok.expires_at)}
                </div>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => revoke.mutate(tok.token)}
                disabled={revoke.isPending}
              >
                {t("settings.share_links.revoke")}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export const Route = createFileRoute("/settings/share-links")({
  component: MyShareLinksPage,
});
