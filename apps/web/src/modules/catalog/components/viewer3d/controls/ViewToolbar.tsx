import {
  Camera,
  Grid3x3,
  Layers,
  PencilRuler,
  RotateCcw,
  Ruler,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/ui/tooltip";

import { TolerancePopover } from "./TolerancePopover";
import type { MeasureMode } from "../types";

type Props = {
  onReset: () => void;
  wireframe: boolean;
  onWireframe: (next: boolean) => void;
  onScreenshot: () => void;
  mode: MeasureMode;
  onMode: (mode: MeasureMode) => void;
  toleranceDeg: number;
  onTolerance: (value: number) => void;
};

function ToolbarButton({
  label,
  active,
  onClick,
  disabled,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={(props) => (
          <Button
            {...props}
            type="button"
            variant="ghost"
            size="icon"
            aria-label={label}
            aria-pressed={active === true ? true : undefined}
            onClick={onClick}
            disabled={disabled === true}
            className={active === true ? "bg-primary/15" : undefined}
          >
            {children}
          </Button>
        )}
      />
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export function ViewToolbar({
  onReset,
  wireframe,
  onWireframe,
  onScreenshot,
  mode,
  onMode,
  toleranceDeg,
  onTolerance,
}: Props) {
  const { t } = useTranslation();
  const toggle = (next: MeasureMode) => onMode(mode === next ? "off" : next);
  return (
    <div className="pointer-events-auto flex items-center gap-1 rounded-md border border-border bg-card/85 px-2 py-1 backdrop-blur">
      <ToolbarButton label={t("viewer3d.tooltip.reset")} onClick={onReset}>
        <RotateCcw className="h-4 w-4" />
      </ToolbarButton>
      <span className="mx-1 h-5 w-px bg-border" aria-hidden />
      <ToolbarButton
        label={t("viewer3d.tooltip.wireframe")}
        active={wireframe}
        onClick={() => onWireframe(!wireframe)}
      >
        <Grid3x3 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton label={t("viewer3d.tooltip.screenshot")} onClick={onScreenshot}>
        <Camera className="h-4 w-4" />
      </ToolbarButton>
      <span className="mx-1 h-5 w-px bg-border" aria-hidden />
      <ToolbarButton
        label={t("viewer3d.measure.mode.p2p")}
        active={mode === "point-to-point"}
        onClick={() => toggle("point-to-point")}
      >
        <Ruler className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        label={t("viewer3d.measure.mode.p2pl")}
        active={mode === "point-to-plane"}
        onClick={() => toggle("point-to-plane")}
      >
        <PencilRuler className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        label={t("viewer3d.measure.mode.pl2pl")}
        active={mode === "plane-to-plane"}
        onClick={() => toggle("plane-to-plane")}
      >
        <Layers className="h-4 w-4" />
      </ToolbarButton>
      <TolerancePopover
        toleranceDeg={toleranceDeg}
        onChange={onTolerance}
        disabled={mode === "off" || mode === "point-to-point"}
      />
    </div>
  );
}
