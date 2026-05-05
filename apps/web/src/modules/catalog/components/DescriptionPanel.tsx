import { useState } from "react";

import type { ModelDetail } from "@/lib/api-types";
import { EditDescriptionSheet } from "@/modules/catalog/components/sheets/EditDescriptionSheet";
import { useAuth } from "@/shell/AuthContext";

export function DescriptionPanel({ detail }: { detail: ModelDetail }) {
  const { isAdmin } = useAuth();
  const [open, setOpen] = useState(false);
  const desc = detail.notes.find((n) => n.kind === "description") ?? null;
  return (
    <section className="relative rounded border border-border bg-card p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Description
        </h3>
        {isAdmin && (
          <button
            type="button"
            aria-label="Edit description"
            onClick={() => setOpen(true)}
            className="text-xs text-muted-foreground opacity-50 hover:opacity-100"
          >
            ✏
          </button>
        )}
      </div>
      {desc !== null ? (
        <div className="whitespace-pre-wrap text-sm text-card-foreground">{desc.body}</div>
      ) : (
        <p className="text-sm text-muted-foreground">no description</p>
      )}
      {isAdmin && (
        <EditDescriptionSheet detail={detail} open={open} onOpenChange={setOpen} />
      )}
    </section>
  );
}
