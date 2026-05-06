import {
  Camera,
  Maximize2,
  Move,
  MousePointer2,
  RotateCcw,
  Ruler,
  Box as BoxIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/ui/tooltip";

import type { ViewPreset } from "../lib/camera";

export type ToolMode = "orbit" | "pan";

type Props = {
  mode: ToolMode;
  onMode: (m: ToolMode) => void;
  onPreset: (p: ViewPreset) => void;
  onReset: () => void;
  wireframe: boolean;
  onWireframe: (next: boolean) => void;
  onScreenshot: () => void;
  measureOn: boolean;
  onMeasureToggle: () => void;
  onExpand?: () => void;
};

function ToolbarButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: ReactNode;
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
            aria-pressed={active === true}
            onClick={onClick}
            className={cn(
              "h-8 w-8",
              active === true && "bg-accent text-accent-foreground",
            )}
          >
            {children}
          </Button>
        )}
      />
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

const PRESETS: ViewPreset[] = ["front", "side", "top", "iso"];

export function ViewToolbar({
  mode,
  onMode,
  onPreset,
  onReset,
  wireframe,
  onWireframe,
  onScreenshot,
  measureOn,
  onMeasureToggle,
  onExpand,
}: Props) {
  const { t } = useTranslation();
  return (
    <div
      role="toolbar"
      aria-label="3D view toolbar"
      className="flex items-center gap-1 rounded-lg border border-border bg-card/85 px-1 py-1 backdrop-blur-md"
    >
      <ToolbarButton label={t("viewer3d.tooltip.reset")} onClick={onReset}>
        <RotateCcw className="h-4 w-4" />
      </ToolbarButton>
      <span className="mx-1 h-5 w-px bg-border" />
      <ToolbarButton
        label={t("viewer3d.tooltip.orbit")}
        active={mode === "orbit"}
        onClick={() => onMode("orbit")}
      >
        <MousePointer2 className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        label={t("viewer3d.tooltip.pan")}
        active={mode === "pan"}
        onClick={() => onMode("pan")}
      >
        <Move className="h-4 w-4" />
      </ToolbarButton>
      <span className="mx-1 h-5 w-px bg-border" />
      {PRESETS.map((p) => (
        <ToolbarButton
          key={p}
          label={t(`viewer3d.tooltip.${p}`)}
          onClick={() => onPreset(p)}
        >
          <span className="text-xs font-mono uppercase">{p[0]}</span>
        </ToolbarButton>
      ))}
      <span className="mx-1 h-5 w-px bg-border" />
      <ToolbarButton
        label={t("viewer3d.tooltip.wireframe")}
        active={wireframe}
        onClick={() => onWireframe(!wireframe)}
      >
        <BoxIcon className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        label={t("viewer3d.tooltip.screenshot")}
        onClick={onScreenshot}
      >
        <Camera className="h-4 w-4" />
      </ToolbarButton>
      <ToolbarButton
        label={t("viewer3d.tooltip.measure")}
        active={measureOn}
        onClick={onMeasureToggle}
      >
        <Ruler className="h-4 w-4" />
      </ToolbarButton>
      {onExpand !== undefined && (
        <>
          <span className="mx-1 h-5 w-px bg-border" />
          <ToolbarButton
            label={t("viewer3d.tooltip.expand")}
            onClick={onExpand}
          >
            <Maximize2 className="h-4 w-4" />
          </ToolbarButton>
        </>
      )}
    </div>
  );
}
