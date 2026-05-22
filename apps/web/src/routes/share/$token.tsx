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
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { fetchShareView, type ShareModelView } from "@/lib/share-api";

function AnonymousShareView({ token }: { token: string }) {
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
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-sm font-semibold text-foreground">{t("share.view.brand")}</span>
          <span className="text-xs text-muted-foreground">{t("share.view.banner_anonymous")}</span>
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

        {(data.thumbnail_url !== null || data.images.length > 0) && (
          <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {data.thumbnail_url !== null && (
              <img
                src={data.thumbnail_url}
                alt={title}
                className="aspect-square w-full rounded border border-border object-cover"
              />
            )}
            {data.images.slice(0, 5).map((url) => (
              <img
                key={url}
                src={url}
                alt={title}
                className="aspect-square w-full rounded border border-border object-cover"
              />
            ))}
          </section>
        )}

        {data.has_3d && data.stl_url !== null && (
          <section className="rounded border border-border bg-card p-4">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t("share.view.stl_label")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("share.view.stl_description")}
            </p>
            <a
              href={data.stl_url}
              download
              className="mt-3 inline-flex items-center rounded border border-border bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              {t("share.view.download_stl")}
            </a>
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
  return <AnonymousShareView token={token} />;
}

export const Route = createFileRoute("/share/$token")({
  // Initiative 10 Story 16.3 — NO AuthGate. AppShell.AuthGate would force a
  // /login redirect for anonymous visitors; this route is intentionally
  // bypassed via the path-prefix `/share/` check in AppShell.tsx
  // `_PUBLIC_PATHS`. Verify the prefix matches at integration time.
  component: ShareTokenRoute,
});
