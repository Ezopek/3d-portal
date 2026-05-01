import { useTranslation } from "react-i18next";

import type { Model } from "@/modules/catalog/types";

export function InfoTab({ model }: { model: Model }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4 p-4 text-sm">
      <dl className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Row label={t("catalog.filters.category")} value={t(`catalog.category.${model.category}`)} />
        <Row label={t("catalog.filters.status")} value={t(`catalog.status.${model.status}`)} />
        <Row label={t("catalog.fields.rating")} value={model.rating === null ? "—" : `${model.rating}/5`} />
        <Row label={t("catalog.fields.date_added")} value={model.date_added} />
        {model.source_url !== null && (
          <Row label={t("catalog.fields.source")} value={
            <a href={model.source_url} target="_blank" rel="noreferrer" className="text-primary underline">
              {model.source}
            </a>
          } />
        )}
      </dl>
      {model.notes !== "" && (
        <div>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">
            {t("catalog.fields.notes")}
          </dt>
          <dd className="mt-1 whitespace-pre-line text-sm text-foreground">{model.notes}</dd>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm text-foreground">{value}</dd>
    </div>
  );
}
