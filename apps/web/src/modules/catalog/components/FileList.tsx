import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { isAdmin } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { useFiles } from "../hooks/useFiles";
import { useRenderSelection, useSetRenderSelection } from "../hooks/useRenderSelection";

const MAX_SELECTION = 16;

export function FileList({ modelId }: { modelId: string }) {
  const { t } = useTranslation();
  const admin = isAdmin();
  const { data: filesData } = useFiles(modelId, { kind: "printable" });
  const { data: selectionData } = useRenderSelection(modelId, { enabled: admin });
  const setSelection = useSetRenderSelection(modelId);

  const [pending, setPending] = useState<Set<string> | null>(null);

  // Reset pending whenever the saved selection changes (server round-trip after Apply).
  useEffect(() => {
    if (selectionData) setPending(null);
  }, [selectionData]);

  if (filesData === undefined) return <p className="p-4 text-sm text-muted-foreground">…</p>;
  if (filesData.files.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">{t("catalog.empty")}</p>;
  }

  const files = filesData.files;
  const savedSet = new Set(selectionData?.paths ?? []);
  const currentSet = pending ?? savedSet;
  const hasPending = pending !== null;
  const tooMany = currentSet.size > MAX_SELECTION;
  const usingDefault = savedSet.size === 0;
  const defaultStl = files[0];

  function toggle(path: string) {
    const next = new Set(currentSet);
    if (next.has(path)) next.delete(path);
    else next.add(path);
    setPending(next);
  }

  async function apply() {
    if (!hasPending || tooMany) return;
    try {
      await setSelection.mutateAsync(Array.from(currentSet));
      toast.success(t("catalog.renderSelection.applied"));
    } catch (err) {
      const message =
        err instanceof ApiError && typeof err.body === "object" && err.body !== null && "detail" in err.body
          ? String((err.body as Record<string, unknown>).detail)
          : t("catalog.renderSelection.errorGeneric");
      toast.error(
        message.startsWith("too_many_files")
          ? t("catalog.renderSelection.errorTooMany")
          : message,
      );
      setPending(null); // rollback
    }
  }

  const status = (() => {
    if (currentSet.size === 0) return t("catalog.renderSelection.statusDefault");
    if (currentSet.size === 1) return t("catalog.renderSelection.statusSingle");
    return t("catalog.renderSelection.statusGroup", { count: currentSet.size });
  })();

  return (
    <div>
      <ul className="divide-y divide-border">
        {files.map((f) => {
          const showAutoBadge = admin && usingDefault && f === defaultStl;
          return (
            <li key={f} className="flex items-center gap-3 px-4 py-2 text-sm">
              {admin && (
                <input
                  type="checkbox"
                  checked={currentSet.has(f)}
                  onChange={() => toggle(f)}
                  aria-label={f}
                />
              )}
              <span className="flex-1 truncate">
                {f}
                {showAutoBadge && (
                  <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {t("catalog.renderSelection.badgeAuto")}
                  </span>
                )}
              </span>
              <a
                href={`/api/files/${modelId}/${f}?download=1`}
                className="flex items-center gap-1 text-primary"
              >
                <Download className="size-4" /> {t("catalog.actions.download")}
              </a>
            </li>
          );
        })}
      </ul>
      {admin && (
        <div className="flex items-center justify-between px-4 py-3 text-sm">
          <div className="flex flex-col">
            <span className="text-muted-foreground">{status}</span>
            {tooMany && (
              <span className="text-xs text-destructive">
                {t("catalog.renderSelection.errorTooMany")}
              </span>
            )}
          </div>
          <button
            type="button"
            disabled={!hasPending || tooMany || setSelection.isPending}
            onClick={apply}
            className="rounded bg-primary px-3 py-1.5 text-primary-foreground disabled:opacity-50"
          >
            {t("catalog.renderSelection.apply")}
          </button>
        </div>
      )}
    </div>
  );
}
