import { Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";

import type { Measurement } from "../types";

type Props = {
  measurements: readonly Measurement[];
  onClear: () => void;
};

export function MeasureSummary({ measurements, onClear }: Props) {
  const { t } = useTranslation();
  const last = measurements.at(-1);

  // While there are no measurements yet, render only the live region —
  // the visible panel would otherwise sit on top of the bottom toolbar
  // on small viewports and intercept pointer events.
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
            #{i + 1} — {m.distanceMm.toFixed(1)} mm
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
