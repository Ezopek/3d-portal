import { useTranslation } from "react-i18next";

import type { Print } from "@/modules/catalog/types";

export function PrintsTab({ modelId, prints }: { modelId: string; prints: Print[] }) {
  const { i18n, t } = useTranslation();
  if (prints.length === 0) return <p className="p-4 text-sm text-muted-foreground">{t("catalog.empty")}</p>;
  return (
    <ul className="grid gap-3 p-4 md:grid-cols-2">
      {prints.map((p) => {
        const note = i18n.language.startsWith("pl") ? p.notes_pl : p.notes_en;
        // Catalog `path` is repo-relative ("category/model_dir/prints/...").
        // Strip the "<category>/<model_dir>/" prefix to get the model-relative path
        // that /api/files/{id}/{...} expects.
        const relative = p.path.split("/").slice(2).join("/");
        return (
          <li key={p.path} className="overflow-hidden rounded-md border border-border bg-card">
            <img src={`/api/files/${modelId}/${relative}`} alt="" className="aspect-square w-full object-cover" />
            <div className="p-3 text-sm">
              <p className="text-xs text-muted-foreground">{p.date}</p>
              {note !== "" && <p className="mt-1">{note}</p>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
