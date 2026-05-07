import { Popover } from "@base-ui/react/popover";
import { Slider } from "@base-ui/react/slider";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

type Props = {
  toleranceDeg: number;
  onChange: (value: number) => void;
  disabled?: boolean;
};

export function TolerancePopover({ toleranceDeg, onChange, disabled }: Props) {
  const { t } = useTranslation();
  return (
    <Popover.Root>
      <Popover.Trigger
        className={cn(
          "inline-flex h-10 min-w-10 items-center justify-center rounded-md px-2 text-xs font-mono text-foreground",
          "border border-border bg-card/60 hover:bg-card",
          disabled === true && "pointer-events-none opacity-50",
        )}
        aria-label={t("viewer3d.measure.tolerance.label")}
        title={t("viewer3d.measure.tolerance.label")}
        disabled={disabled === true}
      >
        {toleranceDeg.toFixed(1)}°
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={8} className="z-[60]">
          <Popover.Popup
            className={cn(
              "z-[60] w-64 rounded-lg border border-border bg-popover p-3 text-popover-foreground shadow-lg",
              "data-starting-style:opacity-0 data-ending-style:opacity-0",
            )}
          >
            <div className="mb-2 text-xs font-medium">
              {t("viewer3d.measure.tolerance.label")}
            </div>
            <Slider.Root
              value={toleranceDeg}
              min={0.5}
              max={15}
              step={0.5}
              onValueChange={(value) => {
                const v = Array.isArray(value) ? value[0] : value;
                if (typeof v === "number") onChange(v);
              }}
              className="flex w-full items-center"
            >
              <Slider.Control className="relative flex h-5 w-full items-center">
                <Slider.Track className="h-1 w-full rounded bg-muted">
                  <Slider.Indicator className="h-1 rounded bg-primary" />
                  <Slider.Thumb
                    className={cn(
                      "ml-[-0.5rem] h-4 w-4 rounded-full border border-primary bg-background shadow",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    )}
                  />
                </Slider.Track>
              </Slider.Control>
            </Slider.Root>
            <div className="mt-2 flex justify-between text-[10px] text-muted-foreground">
              <span>{t("viewer3d.measure.tolerance.tight")}</span>
              <span>{toleranceDeg.toFixed(1)}°</span>
              <span>{t("viewer3d.measure.tolerance.loose")}</span>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              {t("viewer3d.measure.tolerance.help")}
            </p>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
