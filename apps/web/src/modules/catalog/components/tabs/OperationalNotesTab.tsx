import type { NoteRead } from "@/lib/api-types";

const KIND_BORDER: Record<Exclude<NoteRead["kind"], "description">, string> = {
  operational: "border-l-orange-400",
  ai_review: "border-l-blue-400",
  other: "border-l-gray-400",
};

export function OperationalNotesTab({ notes }: { notes: readonly NoteRead[] }) {
  const visible = notes.filter((n) => n.kind !== "description");
  if (visible.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">no notes</p>;
  }
  return (
    <ul className="space-y-3 p-3">
      {visible.map((n) => (
        <li
          key={n.id}
          className={`rounded border border-l-4 border-border ${KIND_BORDER[n.kind as keyof typeof KIND_BORDER]} bg-card p-3 text-sm`}
        >
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {n.kind}
          </div>
          <p className="mt-1 whitespace-pre-wrap">{n.body}</p>
        </li>
      ))}
    </ul>
  );
}
