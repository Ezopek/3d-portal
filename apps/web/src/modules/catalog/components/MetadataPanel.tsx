import { useTranslation } from "react-i18next";

import type { ModelDetail, ModelFileKind } from "@/lib/api-types";

const KIND_LABEL: Record<ModelFileKind, string> = {
  stl: "STL",
  image: "image",
  print: "print",
  source: "source",
  archive_3mf: "3MF",
};

function summariseFiles(files: ModelDetail["files"]): string {
  if (files.length === 0) return "0";
  const counts = new Map<ModelFileKind, number>();
  for (const f of files) counts.set(f.kind, (counts.get(f.kind) ?? 0) + 1);
  const parts = [...counts.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([k, n]) => `${n} ${KIND_LABEL[k]}`);
  return `${files.length} (${parts.join(" · ")})`;
}

export function MetadataPanel({ detail }: { detail: ModelDetail }) {
  const { t, i18n } = useTranslation();
  const filesSummary = summariseFiles(detail.files);
  const dateAdded = (() => {
    const parsed = new Date(detail.date_added);
    if (Number.isNaN(parsed.getTime())) return detail.date_added;
    return parsed.toLocaleDateString(i18n.language);
  })();
  return (
    <section className="rounded border border-border bg-card p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {t("catalog.panels.metadata")}
      </h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">{t("catalog.panels.source")}</dt>
        <dd>{detail.source}</dd>
        <dt className="text-muted-foreground">{t("catalog.panels.added")}</dt>
        <dd>{dateAdded}</dd>
        <dt className="text-muted-foreground">{t("catalog.panels.files")}</dt>
        <dd>{filesSummary}</dd>
        <dt className="text-muted-foreground">{t("catalog.panels.prints")}</dt>
        <dd>{detail.prints.length}</dd>
      </dl>
    </section>
  );
}
