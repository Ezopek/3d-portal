import { useTranslation } from "react-i18next";

import { CATALOG_ESTIMATE_PRINTER_REF } from "@/modules/estimates/lib/preset";
import { AdminTabs } from "@/modules/admin/AdminTabs";
import { useAdminProfiles } from "@/modules/admin/hooks/useAdminProfiles";
import {
  ProfileInventoryGrid,
  ProfileLegend,
} from "@/modules/admin/ProfileInventoryGrid";
import { Button } from "@/ui/button";

/** Loading skeleton matrix (AC-15) — never a bare spinner. */
function GridSkeleton() {
  return (
    <div
      className="grid grid-cols-3 gap-2"
      aria-hidden="true"
      data-testid="profiles-skeleton"
    >
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className="h-10 animate-pulse rounded-md bg-muted" />
      ))}
    </div>
  );
}

/**
 * Story 33.1 (AC-11..AC-16) — the read-only admin profile inventory page.
 *
 * Fails CLOSED/visible (AC-15): a load error shows an error panel with Retry; the grid never
 * fabricates slot statuses or falls open to "all offerable". The empty state IS the
 * all-not-imported grid the backend returns (every slot enumerated), plus a one-line hint.
 */
export function ProfilesPage() {
  const { t } = useTranslation();
  const inventory = useAdminProfiles(CATALOG_ESTIMATE_PRINTER_REF);

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="profiles" />

      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">
          {t("modules.admin.profiles.title")}
        </h1>
        <p className="text-xs text-muted-foreground">
          {t("modules.admin.profiles.printer_context")}:{" "}
          <span className="text-foreground">
            {t("modules.admin.profiles.printer_label")}
          </span>{" "}
          · {t("modules.admin.profiles.single_printer_note")}
        </p>
      </header>

      {inventory.isError ? (
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.profiles.error_title")}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void inventory.refetch()}
          >
            {t("modules.admin.profiles.retry")}
          </Button>
        </div>
      ) : inventory.isLoading ? (
        <GridSkeleton />
      ) : inventory.data ? (
        <>
          <ProfileLegend />
          <ProfileInventoryGrid
            slots={inventory.data.slots}
            printerRef={inventory.data.printer_ref}
          />
          {inventory.data.slots.every((slot) => !slot.offerable) ? (
            <p className="text-xs text-muted-foreground">
              {t("modules.admin.profiles.empty_hint")}
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
