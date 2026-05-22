import { Pencil } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { EditDescriptionSheet } from "@/modules/catalog/components/sheets/EditDescriptionSheet";
import { useAuth } from "@/shell/AuthContext";

export function DescriptionPanel({ detail }: { detail: ModelDetail }) {
  const { t, i18n } = useTranslation();
  const { isAdmin } = useAuth();
  const [open, setOpen] = useState(false);
  const desc = detail.notes.find((n) => n.kind === "description") ?? null;
  // Initiative 10 Story 16.1 (Decision L) — bilingual fallback chain. Prefer
  // current-locale field, fall back to the other locale, finally fall back to
  // legacy `body` so pre-migration descriptions still render. Order matters:
  // a Polish user with body_pl=null and body_en="..." sees the English text
  // rather than nothing.
  const localePreference = i18n.language?.toLowerCase().startsWith("pl")
    ? ([desc?.body_pl, desc?.body_en] as const)
    : ([desc?.body_en, desc?.body_pl] as const);
  const resolvedBody =
    localePreference.find((value) => value && value.length > 0) ?? desc?.body ?? null;
  return (
    <section className="relative rounded border border-border bg-card p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t("catalog.panels.description")}
        </h3>
        {isAdmin && (
          <button
            type="button"
            aria-label={t("catalog.actions.editDescription")}
            onClick={() => setOpen(true)}
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground opacity-50 hover:bg-accent hover:opacity-100"
          >
            <Pencil className="size-3" aria-hidden />
          </button>
        )}
      </div>
      {resolvedBody !== null && resolvedBody.length > 0 ? (
        <div className="whitespace-pre-wrap text-sm text-card-foreground">{resolvedBody}</div>
      ) : (
        <p className="text-sm text-muted-foreground">{t("catalog.empty.description")}</p>
      )}
      {isAdmin && (
        <EditDescriptionSheet detail={detail} open={open} onOpenChange={setOpen} />
      )}
    </section>
  );
}
