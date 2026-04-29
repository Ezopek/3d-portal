import { Download } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useFiles } from "../hooks/useFiles";

export function FileList({ modelId }: { modelId: string }) {
  const { t } = useTranslation();
  const { data } = useFiles(modelId);
  if (data === undefined) return <p className="p-4 text-sm text-muted-foreground">…</p>;
  if (data.files.length === 0) return <p className="p-4 text-sm text-muted-foreground">{t("catalog.empty")}</p>;
  return (
    <ul className="divide-y divide-border">
      {data.files.map((f) => (
        <li key={f} className="flex items-center justify-between px-4 py-2 text-sm">
          <span className="truncate">{f}</span>
          <a href={`/api/files/${modelId}/${f}`} className="flex items-center gap-1 text-primary">
            <Download className="size-4" /> {t("catalog.actions.download_stl")}
          </a>
        </li>
      ))}
    </ul>
  );
}
