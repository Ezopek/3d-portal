import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { NoteRead } from "@/lib/api-types";
import { AddNoteSheet } from "@/modules/catalog/components/sheets/AddNoteSheet";
import { useDeleteNote } from "@/modules/catalog/hooks/mutations/useDeleteNote";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";

const KIND_BORDER: Record<Exclude<NoteRead["kind"], "description">, string> = {
  operational: "border-l-warning",
  ai_review: "border-l-primary",
  other: "border-l-muted-foreground",
};

export function OperationalNotesTab({
  modelId,
  notes,
}: {
  modelId: string;
  notes: readonly NoteRead[];
}) {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState<NoteRead | null>(null);
  const del = useDeleteNote(modelId);

  const visible = notes.filter((n) => n.kind !== "description");

  function openAdd() {
    setEditing(null);
    setSheetOpen(true);
  }

  function openEdit(note: NoteRead) {
    setEditing(note);
    setSheetOpen(true);
  }

  function confirmDelete(noteId: string) {
    if (window.confirm(t("catalog.actions.confirmDeleteNote"))) {
      del.mutate(noteId);
    }
  }

  return (
    <>
      {isAdmin && (
        <div className="flex justify-end p-3 pb-0">
          <Button size="sm" onClick={openAdd}>
            {t("catalog.actions.addNote")}
          </Button>
        </div>
      )}
      {visible.length === 0 ? (
        <p className="p-4 text-sm text-muted-foreground">{t("catalog.empty.notes")}</p>
      ) : (
        <ul className="space-y-3 p-3">
          {visible.map((n) => (
            <li
              key={n.id}
              className={`flex items-start gap-2 rounded border border-l-4 border-border ${KIND_BORDER[n.kind as keyof typeof KIND_BORDER]} bg-card p-3 text-sm`}
            >
              <div className="min-w-0 flex-1">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  {n.kind}
                </div>
                <p className="mt-1 whitespace-pre-wrap">{n.body}</p>
              </div>
              {isAdmin && (
                <div className="flex items-start gap-1">
                  <button
                    type="button"
                    aria-label={t("catalog.actions.editNote")}
                    onClick={() => openEdit(n)}
                    className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground opacity-50 hover:bg-accent hover:opacity-100"
                  >
                    <Pencil className="size-3" aria-hidden />
                  </button>
                  <button
                    type="button"
                    aria-label={t("catalog.actions.deleteNote")}
                    onClick={() => confirmDelete(n.id)}
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
        <AddNoteSheet
          modelId={modelId}
          note={editing}
          open={sheetOpen}
          onOpenChange={setSheetOpen}
        />
      )}
    </>
  );
}
