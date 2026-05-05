import { useState } from "react";

import type { NoteRead } from "@/lib/api-types";
import { AddNoteSheet } from "@/modules/catalog/components/sheets/AddNoteSheet";
import { useDeleteNote } from "@/modules/catalog/hooks/mutations/useDeleteNote";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";

const KIND_BORDER: Record<Exclude<NoteRead["kind"], "description">, string> = {
  operational: "border-l-orange-400",
  ai_review: "border-l-blue-400",
  other: "border-l-gray-400",
};

export function OperationalNotesTab({
  modelId,
  notes,
}: {
  modelId: string;
  notes: readonly NoteRead[];
}) {
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
    if (window.confirm("Delete this note?")) {
      del.mutate(noteId);
    }
  }

  return (
    <>
      {isAdmin && (
        <div className="flex justify-end p-3 pb-0">
          <Button size="sm" onClick={openAdd}>
            + Add note
          </Button>
        </div>
      )}
      {visible.length === 0 ? (
        <p className="p-4 text-sm text-muted-foreground">no notes</p>
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
                    aria-label="Edit note"
                    onClick={() => openEdit(n)}
                    className="text-xs text-muted-foreground opacity-50 hover:opacity-100"
                  >
                    ✏
                  </button>
                  <button
                    type="button"
                    aria-label="Delete note"
                    onClick={() => confirmDelete(n.id)}
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
