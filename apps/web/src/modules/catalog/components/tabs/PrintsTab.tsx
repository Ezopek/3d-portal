import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { PrintRead } from "@/lib/api-types";
import { AddPrintSheet } from "@/modules/catalog/components/sheets/AddPrintSheet";
import { useDeletePrint } from "@/modules/catalog/hooks/mutations/useDeletePrint";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import { EmptyState } from "@/ui/custom/EmptyState";

export function PrintsTab({
  modelId,
  prints,
}: {
  modelId: string;
  prints: readonly PrintRead[];
}) {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState<PrintRead | null>(null);
  const del = useDeletePrint(modelId);

  function openAdd() {
    setEditing(null);
    setSheetOpen(true);
  }

  function openEdit(print: PrintRead) {
    setEditing(print);
    setSheetOpen(true);
  }

  function confirmDelete(printId: string) {
    if (window.confirm(t("catalog.actions.confirmDeletePrint"))) {
      del.mutate(printId);
    }
  }

  return (
    <>
      {isAdmin && (
        <div className="flex justify-end p-3 pb-0">
          <Button size="sm" onClick={openAdd}>
            {t("catalog.actions.addPrint")}
          </Button>
        </div>
      )}
      {prints.length === 0 ? (
        isAdmin ? (
          <EmptyState
            messageKey="catalog.empty.prints"
            action={{ labelKey: "catalog.actions.addPrint", onClick: openAdd }}
          />
        ) : (
          <p className="p-4 text-sm text-muted-foreground">
            {t("catalog.empty.prints")}
          </p>
        )
      ) : (
        <ul className="space-y-3 p-3">
          {prints.map((p) => (
            <li
              key={p.id}
              className="grid grid-cols-[80px_1fr_auto] gap-3 rounded border border-border bg-card p-3"
            >
              {p.photo_file_id !== null ? (
                <img
                  src={`/api/models/${modelId}/files/${p.photo_file_id}/content`}
                  alt=""
                  className="aspect-square rounded bg-muted object-cover"
                />
              ) : (
                <div className="aspect-square rounded bg-muted" />
              )}
              <div className="text-sm">
                <div className="font-medium">{p.printed_at ?? "—"}</div>
                {p.note !== null && p.note !== "" && (
                  <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
                    {p.note}
                  </p>
                )}
              </div>
              {isAdmin && (
                <div className="flex items-start gap-1">
                  <button
                    type="button"
                    aria-label={t("catalog.actions.editPrint")}
                    onClick={() => openEdit(p)}
                    className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground opacity-50 hover:bg-accent hover:opacity-100"
                  >
                    <Pencil className="size-3" aria-hidden />
                  </button>
                  <button
                    type="button"
                    aria-label={t("catalog.actions.deletePrint")}
                    onClick={() => confirmDelete(p.id)}
                    className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground opacity-50 hover:bg-accent hover:opacity-100"
                  >
                    <Trash2 className="size-3" aria-hidden />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {isAdmin && (
        <AddPrintSheet
          modelId={modelId}
          print={editing}
          open={sheetOpen}
          onOpenChange={setSheetOpen}
        />
      )}
    </>
  );
}
