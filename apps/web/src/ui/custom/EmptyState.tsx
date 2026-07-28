import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";

interface Props {
  messageKey: string;
  /** Interpolation values for `messageKey`, e.g. `{ name: "Uchwyty" }`. Additive
   *  and optional (Story 51.2 D-9): every existing caller renders unchanged. */
  messageParams?: Record<string, string | number>;
  icon?: ReactNode;
  action?: { labelKey: string; onClick: () => void };
  secondaryAction?: { labelKey: string; onClick: () => void };
  tone?: "muted" | "error";
}

export function EmptyState({
  messageKey,
  messageParams,
  icon,
  action,
  secondaryAction,
  tone = "muted",
}: Props) {
  const { t } = useTranslation();
  const toneClass =
    tone === "error" ? "text-destructive" : "text-muted-foreground";
  return (
    <div className="grid place-items-center p-12 text-center">
      <div className="space-y-3">
        {icon !== undefined && (
          <div className={cn("flex justify-center", toneClass)}>{icon}</div>
        )}
        <p className={cn("text-sm", toneClass)}>
          {t(messageKey, messageParams)}
        </p>
        {action !== undefined && (
          <div className="flex justify-center gap-2">
            <Button variant="outline" onClick={action.onClick}>
              {t(action.labelKey)}
            </Button>
            {secondaryAction !== undefined && (
              <Button variant="outline" onClick={secondaryAction.onClick}>
                {t(secondaryAction.labelKey)}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
