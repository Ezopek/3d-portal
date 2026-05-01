import type { CSSProperties } from "react";

interface Props { src: string }

// TODO: <model-viewer> 4.x natively supports glTF/GLB. STL loading may fail silently.
// Future improvement: convert STL→GLB server-side or fall back to three.js + STLLoader.
export function ModelViewer({ src }: Props) {
  // <model-viewer>'s WebGL canvas defaults to a hardcoded clearColor that
  // ignores CSS theme. Setting backgroundColor: transparent lets the wrapper's
  // bg-muted (theme-aware) show through; --poster-color keeps the loading
  // poster matching the muted token in both palettes.
  const viewerStyle = {
    width: "100%",
    height: "100%",
    backgroundColor: "transparent",
    "--poster-color": "var(--color-muted)",
  } as CSSProperties;
  return (
    <div className="mx-auto aspect-square w-full max-w-[70vh] overflow-hidden rounded-md bg-muted">
      <model-viewer
        src={src}
        alt=""
        camera-controls
        auto-rotate
        style={viewerStyle}
      />
    </div>
  );
}
