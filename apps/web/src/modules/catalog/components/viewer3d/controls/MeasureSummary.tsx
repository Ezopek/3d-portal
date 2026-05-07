import { Trash2 } from "lucide-react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";

import type { Measurement } from "../types";

type Props = {
  measurements: readonly Measurement[];
  onClear: () => void;
};

function formatRow(m: Measurement, t: TFunction): string {
  const value = m.distanceMm.toFixed(1);
  let base: string;
  if (m.kind === "p2p") {
    base = t("viewer3d.measure.label", { value });
  } else if (m.kind === "p2pl") {
    base = t("viewer3d.measure.row.p2pl", { value });
  } else {
    const angle = m.angleDeg.toFixed(1);
    base =
      m.pl2plKind === "parallel"
        ? t("viewer3d.measure.row.pl2pl_parallel", { value, angle })
        : t("viewer3d.measure.row.pl2pl_closest", { value, angle });
  }
  if (m.kind === "pl2pl" && m.approximate) {
    base += t("viewer3d.measure.row.approximate_suffix");
  }
  const weak =
    (m.kind === "p2pl" && m.weakA) ||
    (m.kind === "pl2pl" && (m.weakA || m.weakB));
  if (weak) base += t("viewer3d.measure.row.weak_suffix");
  return base;
}

export function MeasureSummary({ measurements, onClear }: Props) {
  const { t } = useTranslation();
  const last = measurements.at(-1);

  if (measurements.length === 0) {
    return (
      <div role="status" aria-live="polite" className="sr-only">
        {""}
      </div>
    );
  }

  return (
    <div className="pointer-events-auto rounded-lg border border-border bg-card/85 px-3 py-2 backdrop-blur-md">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-xs font-medium text-foreground">
          {t("viewer3d.measure.summary_title")} ({measurements.length})
        </h4>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={t("viewer3d.measure.clear")}
          onClick={onClear}
          className="h-6 w-6"
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
      <ul className="mt-1 space-y-0.5 text-xs font-mono text-foreground">
        {measurements.map((m, i) => (
          <li key={m.id}>
            #{i + 1} — {formatRow(m, t)}
          </li>
        ))}
      </ul>
      <div role="status" aria-live="polite" className="sr-only">
        {last !== undefined
          ? t("viewer3d.measure.live", { value: Math.round(last.distanceMm) })
          : ""}
      </div>
    </div>
  );
}
