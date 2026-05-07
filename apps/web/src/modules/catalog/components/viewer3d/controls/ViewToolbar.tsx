import {
  Camera,
  Grid3x3,
  Ruler,
  RotateCcw,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/ui/tooltip";

type Props = {
  onReset: () => void;
  wireframe: boolean;
  onWireframe: (next: boolean) => void;
  onScreenshot: () => void;
  measureOn: boolean;
  onMeasureToggle: () => void;
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
  measureOn,
  onMeasureToggle,
}: Props) {
  const { t } = useTranslation();
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
        label={t("viewer3d.tooltip.measure")}
        active={measureOn}
        onClick={onMeasureToggle}
      >
        <Ruler className="h-4 w-4" />
      </ToolbarButton>
    </div>
  );
}
