import { SourceBadge } from "portal-web";

export function Sources() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <SourceBadge source="printables" />
      <SourceBadge source="thingiverse" />
      <SourceBadge source="makerworld" />
      <SourceBadge source="cults3d" />
      <SourceBadge source="thangs" />
      <SourceBadge source="own" />
    </div>
  );
}
