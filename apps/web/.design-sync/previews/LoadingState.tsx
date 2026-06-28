import { LoadingState } from "portal-web";

export function Spinner() {
  return (
    <div className="w-72">
      <LoadingState variant="spinner" />
    </div>
  );
}

export function SkeletonGrid() {
  return (
    <div className="w-[28rem]">
      <LoadingState variant="skeleton-grid" cols={3} rows={2} />
    </div>
  );
}

export function SkeletonDetail() {
  return (
    <div className="w-[32rem]">
      <LoadingState variant="skeleton-detail" />
    </div>
  );
}
