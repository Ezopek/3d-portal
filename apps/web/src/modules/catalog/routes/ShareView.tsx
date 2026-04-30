import { useParams } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { useShare } from "@/modules/catalog/hooks/useShare";
import { Button } from "@/ui/button";
import { Gallery } from "@/ui/custom/Gallery";

export function ShareView() {
  const { token } = useParams({ from: "/share/$token" });
  const { i18n, t } = useTranslation();
  const { data, isError, isLoading } = useShare(token);

  if (isLoading) {
    return <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">…</div>;
  }
  if (isError || data === undefined) {
    return (
      <div className="grid min-h-screen place-items-center text-sm text-destructive">
        {t("errors.not_found")}
      </div>
    );
  }

  const primary = i18n.language.startsWith("pl") ? data.name_pl : data.name_en;
  const note = i18n.language.startsWith("pl") ? data.notes_pl : data.notes_en;

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <span className="text-sm font-semibold">{t("app.name")}</span>
        <span className="text-xs text-muted-foreground">{t("share.tagline")}</span>
      </header>
      <Gallery images={data.images} />
      <h1 className="mt-4 text-2xl font-semibold">{primary}</h1>
      {note !== "" && <p className="mt-2 text-sm text-muted-foreground">{note}</p>}
      {data.stl_url !== null && (
        <div className="mt-4">
          <Button variant="default" render={<a href={data.stl_url} />}>
            {t("catalog.actions.download_stl")}
          </Button>
        </div>
      )}
      <footer className="mt-12 text-center text-xs text-muted-foreground">
        3D Portal · ezop
      </footer>
    </div>
  );
}
