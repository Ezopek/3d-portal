import { useState } from "react";

import type { PrintRead } from "@/lib/api-types";
import { AddPrintSheet } from "@/modules/catalog/components/sheets/AddPrintSheet";
import { useDeletePrint } from "@/modules/catalog/hooks/mutations/useDeletePrint";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";

export function PrintsTab({
  modelId,
  prints,
}: {
  modelId: string;
  prints: readonly PrintRead[];
}) {
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
    if (window.confirm("Delete this print?")) {
      del.mutate(printId);
    }
  }

  return (
    <>
      {isAdmin && (
        <div className="flex justify-end p-3 pb-0">
          <Button size="sm" onClick={openAdd}>
            + Add print
          </Button>
        </div>
      )}
      {prints.length === 0 ? (
        <p className="p-4 text-sm text-muted-foreground">no prints</p>
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
                    aria-label="Edit print"
                    onClick={() => openEdit(p)}
                    className="text-xs text-muted-foreground opacity-50 hover:opacity-100"
                  >
                    ✏
                  </button>
                  <button
                    type="button"
                    aria-label="Delete print"
                    onClick={() => confirmDelete(p.id)}
                    className="text-xs text-muted-foreground opacity-50 hover:opacity-100"
                  >
                    🗑
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
