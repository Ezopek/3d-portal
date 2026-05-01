interface Props { src: string }

// TODO: <model-viewer> 4.x natively supports glTF/GLB. STL loading may fail silently.
// Future improvement: convert STL→GLB server-side or fall back to three.js + STLLoader.
export function ModelViewer({ src }: Props) {
  return (
    <div className="mx-auto aspect-square w-full max-w-[70vh] overflow-hidden rounded-md bg-muted">
      <model-viewer
        src={src}
        alt=""
        camera-controls
        auto-rotate
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
