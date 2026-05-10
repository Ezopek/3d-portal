import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

type Variant = "spinner" | "skeleton-grid" | "skeleton-detail";

interface Props {
  variant?: Variant;
  cols?: number;
  rows?: number;
  className?: string;
  label?: string;
}

export function LoadingState({
  variant = "spinner",
  cols = 4,
  rows = 3,
  className,
  label,
}: Props) {
  const { t } = useTranslation();
  const ariaLabel = label ?? t("common.loading");

  if (variant === "spinner") {
    return (
      <div
        role="status"
        aria-label={ariaLabel}
        className={cn("flex items-center justify-center p-6", className)}
      >
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (variant === "skeleton-grid") {
    const cells = Array.from({ length: cols * rows }, (_, i) => i);
    return (
      <div
        role="status"
        aria-label={ariaLabel}
        className={cn("p-3", className)}
      >
        <div
          className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
          aria-hidden
        >
          {cells.map((i) => (
            <div
              key={i}
              className="aspect-square animate-pulse rounded-md bg-muted"
            />
          ))}
        </div>
      </div>
    );
  }

  // skeleton-detail
  return (
    <div
      role="status"
      aria-label={ariaLabel}
      className={cn("space-y-4 p-4", className)}
    >
      <div className="space-y-2" aria-hidden>
        <div className="h-6 w-1/2 animate-pulse rounded bg-muted" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-muted/70" />
      </div>
      <div
        className="grid grid-cols-1 gap-4 md:grid-cols-[36%_1fr]"
        aria-hidden
      >
        <div className="aspect-[4/3] animate-pulse rounded-md bg-muted" />
        <div className="space-y-3">
          <div className="h-24 animate-pulse rounded-md bg-muted/70" />
          <div className="h-16 animate-pulse rounded-md bg-muted/70" />
          <div className="h-32 animate-pulse rounded-md bg-muted/70" />
        </div>
      </div>
      <div className="h-10 animate-pulse rounded-md bg-muted/70" aria-hidden />
    </div>
  );
}
