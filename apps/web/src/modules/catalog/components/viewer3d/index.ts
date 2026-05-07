import { lazy } from "react";

export type { StlFile, Viewer3DProps, MeasureMode, MeasureState, Measurement } from "./types";
export type { Viewer3DInlineProps } from "./Viewer3DInline";

export const Viewer3DInline = lazy(() => import("./Viewer3DInline"));
export const Viewer3DModal = lazy(() => import("./Viewer3DModal"));
