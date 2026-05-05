import type { ExternalLinkRead } from "@/lib/api-types";

export function ExternalLinksPanel({ links }: { links: readonly ExternalLinkRead[] }) {
  if (links.length === 0) return null;
  return (
    <section className="rounded border border-border bg-card p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        External links
      </h3>
      <ul className="space-y-1">
        {links.map((link) => (
          <li key={link.id} className="flex items-start gap-2 text-sm">
            <span aria-hidden className="mt-0.5">↗</span>
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="min-w-0 flex-1 break-all text-foreground hover:underline"
            >
              {link.url}
            </a>
            <span className="mt-0.5 shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
              {link.source}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
