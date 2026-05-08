import { Trash2, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { cn } from "@/lib/utils";

import { paletteCss } from "../lib/palette";
import type { Measurement } from "../types";
import { formatMm } from "../measure/geometry";

type Props = {
  measurements: readonly Measurement[];
  onClear: () => void;
  onDelete: (id: string) => void;
};

function rowText(m: Measurement, t: ReturnType<typeof useTranslation>["t"]): string {
  if (m.kind === "p2p") return formatMm(m.distanceMm);
  if (m.kind === "p2pl") return formatMm(m.distanceMm);
  if (m.kind === "pl2pl") return `${formatMm(m.distanceMm)} @ ${m.angleDeg.toFixed(1)}°`;
  // diameter — i18n template adds "mm", pass raw number string only
  const value = m.diameterMm.toFixed(1);
  return m.weak
    ? t("viewer3d.measure.diameter.weak", { value })
    : t("viewer3d.measure.diameter.format", { value });
}

function hasSel2(m: Measurement): boolean {
  return m.kind !== "diameter";
}

export function MeasureSummary({ measurements, onClear, onDelete }: Props) {
  const { t } = useTranslation();
  if (measurements.length === 0) {
    return (
      <p className="px-2 py-1 text-xs text-muted-foreground">
        {t("viewer3d.measure.summary.empty")}
      </p>
    );
  }
  return (
    <div className="rounded-md border border-border bg-card/85 backdrop-blur-md text-xs">
      <ul className="divide-y divide-border">
        {measurements.map((m, i) => {
          const sel1 = paletteCss(m.colorIndex, "sel1");
          const sel2 = paletteCss(m.colorIndex, "sel2");
          return (
            <li
              key={m.id}
              className="flex items-center gap-2 px-2 py-1 pointer-events-auto"
            >
              <span className="inline-flex items-center gap-0.5">
                <span
                  className="h-2.5 w-2.5 rounded-sm border border-border"
                  style={{ background: sel1 }}
                />
                {hasSel2(m) && (
                  <span
                    className="h-2.5 w-2.5 rounded-sm border border-border"
                    style={{ background: sel2 }}
                  />
                )}
              </span>
              <span className="font-mono text-muted-foreground">#{i + 1}</span>
              <span className="flex-1 font-mono">{rowText(m, t)}</span>
              <button
                type="button"
                onClick={() => onDelete(m.id)}
                className={cn(
                  "rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground",
                  "transition-colors",
                )}
                aria-label={t("viewer3d.measure.delete_one")}
                title={t("viewer3d.measure.delete_one")}
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          );
        })}
      </ul>
      <div className="px-2 py-1 border-t border-border">
        <Button type="button" variant="ghost" size="sm" onClick={onClear} className="h-6 gap-1">
          <Trash2 className="h-3 w-3" />
          {t("viewer3d.measure.clear")}
        </Button>
      </div>
    </div>
  );
}
