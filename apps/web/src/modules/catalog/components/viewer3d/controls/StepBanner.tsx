import { X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";
import { cn } from "@/lib/utils";

import type { MeasureMode } from "../types";

type Stage = "empty" | "have-point" | "have-plane";

type Props = {
  mode: MeasureMode;
  stage: Stage;
  loading: boolean;
  error: string | null;
  onDismissError: () => void;
  /** When provided, overrides the default `top-12` for layouts where the
   * banner sits closer to the canvas edge (inline view has no FileSelector). */
  position?: "modal" | "inline";
};

function pickKey(
  mode: MeasureMode,
  stage: Stage,
  loading: boolean,
  error: string | null,
): { key: string; isError: boolean } | null {
  if (error !== null) return { key: "viewer3d.welding_failed", isError: true };
  if (
    loading &&
    (mode === "point-to-plane" || mode === "plane-to-plane" || mode === "diameter")
  ) {
    return { key: "viewer3d.measure.step.preparing", isError: false };
  }
  if (mode === "off") return null;
  if (mode === "point-to-point") {
    return {
      key:
        stage === "have-point"
          ? "viewer3d.measure.step.p2p_b"
          : "viewer3d.measure.step.p2p_a",
      isError: false,
    };
  }
  if (mode === "point-to-plane") {
    return {
      key:
        stage === "have-plane"
          ? "viewer3d.measure.step.p2pl_point"
          : "viewer3d.measure.step.p2pl_plane",
      isError: false,
    };
  }
  if (mode === "diameter") {
    return { key: "viewer3d.measure.diameter.help", isError: false };
  }
  return {
    key:
      stage === "have-plane"
        ? "viewer3d.measure.step.pl2pl_b"
        : "viewer3d.measure.step.pl2pl_a",
    isError: false,
  };
}

export function StepBanner({
  mode,
  stage,
  loading,
  error,
  onDismissError,
  position = "modal",
}: Props) {
  const { t } = useTranslation();
  const picked = pickKey(mode, stage, loading, error);
  if (picked === null) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "absolute left-1/2 z-10 -translate-x-1/2 rounded-full border px-3 py-1.5 text-xs backdrop-blur-md",
        position === "modal" ? "top-12" : "top-3",
        picked.isError
          ? "border-destructive/50 bg-destructive/15 text-destructive-foreground"
          : "border-primary/40 bg-card/85 text-foreground",
        "flex items-center gap-2",
      )}
    >
      <span>{t(picked.key)}</span>
      {picked.isError && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={t("viewer3d.welding_failed.dismiss")}
          title={t("viewer3d.welding_failed.dismiss")}
          onClick={onDismissError}
          className="h-5 w-5"
        >
          <X className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
