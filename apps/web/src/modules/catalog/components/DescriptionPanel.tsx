import type { NoteRead } from "@/lib/api-types";

export function DescriptionPanel({ notes }: { notes: readonly NoteRead[] }) {
  const desc = notes.find((n) => n.kind === "description") ?? null;
  return (
    <section className="rounded border border-border bg-card p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Description
      </h3>
      {desc !== null ? (
        <div className="whitespace-pre-wrap text-sm text-card-foreground">{desc.body}</div>
      ) : (
        <p className="text-sm text-muted-foreground">no description</p>
      )}
    </section>
  );
}
