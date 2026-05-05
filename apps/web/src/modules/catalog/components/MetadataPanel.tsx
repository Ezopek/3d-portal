import type { ModelDetail, ModelFileKind } from "@/lib/api-types";

const KIND_LABEL: Record<ModelFileKind, string> = {
  stl: "STL",
  image: "image",
  print: "print",
  source: "source",
  archive_3mf: "3MF",
};

function summariseFiles(files: ModelDetail["files"]): string {
  if (files.length === 0) return "0";
  const counts = new Map<ModelFileKind, number>();
  for (const f of files) counts.set(f.kind, (counts.get(f.kind) ?? 0) + 1);
  const parts = [...counts.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([k, n]) => `${n} ${KIND_LABEL[k]}`);
  return `${files.length} (${parts.join(" · ")})`;
}

export function MetadataPanel({ detail }: { detail: ModelDetail }) {
  const filesSummary = summariseFiles(detail.files);
  return (
    <section className="rounded border border-border bg-card p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Metadata
      </h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Source</dt>
        <dd>{detail.source}</dd>
        <dt className="text-muted-foreground">Added</dt>
        <dd>{detail.date_added}</dd>
        <dt className="text-muted-foreground">Files</dt>
        <dd>{filesSummary}</dd>
        <dt className="text-muted-foreground">Prints</dt>
        <dd>{detail.prints.length}</dd>
      </dl>
    </section>
  );
}
