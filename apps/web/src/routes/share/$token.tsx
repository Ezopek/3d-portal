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
            {/* NFR10-SHARE-SECURITY-1 — crossOrigin="anonymous" forces the
                browser into anonymous-credentials mode for these img
                requests (no cookies sent). Otherwise a logged-in user
                viewing /share/<token> would attach their portal_access
                cookie to every gallery image request and update
                last_active_at against the anonymous share path. */}
            {data.thumbnail_url !== null && (
              <img
                src={data.thumbnail_url}
                alt={title}
                crossOrigin="anonymous"
                className="aspect-square w-full rounded border border-border object-cover"
              />
            )}
            {data.images.slice(0, 5).map((url) => (
              <img
                key={url}
                src={url}
                alt={title}
                crossOrigin="anonymous"
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
  return <AnonymousShareView token={token} />;
}

export const Route = createFileRoute("/share/$token")({
  // Initiative 10 Story 16.3 — NO AuthGate. AppShell.AuthGate would force a
  // /login redirect for anonymous visitors; this route is intentionally
  // bypassed via the path-prefix `/share/` check in AppShell.tsx
  // `_PUBLIC_PATHS`. Verify the prefix matches at integration time.
  component: ShareTokenRoute,
});
