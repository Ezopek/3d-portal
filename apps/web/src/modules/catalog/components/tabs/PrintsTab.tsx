import type { PrintRead } from "@/lib/api-types";

export function PrintsTab({
  modelId,
  prints,
}: {
  modelId: string;
  prints: readonly PrintRead[];
}) {
  if (prints.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">no prints</p>;
  }
  return (
    <ul className="space-y-3 p-3">
      {prints.map((p) => (
        <li
          key={p.id}
          className="grid grid-cols-[80px_1fr] gap-3 rounded border border-border bg-card p-3"
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
        </li>
      ))}
    </ul>
  );
}
