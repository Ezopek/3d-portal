import { Pencil } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import { EditDescriptionSheet } from "@/modules/catalog/components/sheets/EditDescriptionSheet";
import { useAuth } from "@/shell/AuthContext";

export function DescriptionPanel({ detail }: { detail: ModelDetail }) {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const [open, setOpen] = useState(false);
  const desc = detail.notes.find((n) => n.kind === "description") ?? null;
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
      {desc !== null ? (
        <div className="whitespace-pre-wrap text-sm text-card-foreground">{desc.body}</div>
      ) : (
        <p className="text-sm text-muted-foreground">{t("catalog.empty.description")}</p>
      )}
      {isAdmin && (
        <EditDescriptionSheet detail={detail} open={open} onOpenChange={setOpen} />
      )}
    </section>
  );
}
