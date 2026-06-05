import {
  Ban,
  CheckCircle2,
  CircleDashed,
  Copy,
  Info,
  TriangleAlert,
} from "lucide-react";
import { useRef, type ChangeEvent, type ComponentType } from "react";
import { useTranslation } from "react-i18next";

import type { AdminProfileSlot, AdminProfileStatus } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import {
  importRejectionCategory,
  useImportProfile,
} from "@/modules/admin/hooks/useImportProfile";
import {
  MATERIAL_CLASSES,
  QUALITY_TIERS,
} from "@/modules/estimates/lib/preset";
import { Button } from "@/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

// Status → presentation. AC-13: Offerable is the ONLY saturated-positive status
// (`--color-success`); Not resolvable is the only warning (`--color-warning`); Incompatible
// is the most de-emphasised; Not imported is neutral. No two statuses share a color, and
// status is NEVER conveyed by color alone — every cell carries icon + text label + color.
// Zero inline hex: all colors are theme-token Tailwind classes (AC-23).
const STATUS_PRESENTATION: Record<
  AdminProfileStatus,
  { icon: ComponentType<{ className?: string }>; className: string }
> = {
  offerable: { icon: CheckCircle2, className: "bg-success/10 text-success" },
  not_imported: {
    icon: CircleDashed,
    className: "border border-dashed border-border text-muted-foreground",
  },
  not_resolvable: { icon: TriangleAlert, className: "bg-warning/10 text-warning" },
  incompatible: { icon: Ban, className: "text-muted-foreground opacity-70" },
};

// Short display form of the provenance tree hash (AC-14). 12 chars is an arbitrary
// readability default (explicitly NOT a contract — the full value is copyable via the
// popover); no contract pins 12.
const SHORT_HASH_CHARS = 12;

const STATUS_ORDER: AdminProfileStatus[] = [
  "offerable",
  "not_imported",
  "not_resolvable",
  "incompatible",
];

/** Always-visible legend (AC-12): the four statuses with icon + color + one-line meaning. */
export function ProfileLegend() {
  const { t } = useTranslation();
  return (
    <div
      className="flex flex-wrap gap-x-4 gap-y-1 rounded-md border border-border bg-card p-2 text-xs"
      aria-label={t("modules.admin.profiles.legend.title")}
    >
      {STATUS_ORDER.map((status) => (
        <div key={status} className="flex items-center gap-1.5">
          <StatusBadge status={status} />
          <span className="text-muted-foreground">
            {t(`modules.admin.profiles.legend.${status}`)}
          </span>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: AdminProfileStatus }) {
  const { t } = useTranslation();
  const { icon: Icon, className } = STATUS_PRESENTATION[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium",
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden="true" />
      {t(`modules.admin.profiles.status.${status}`)}
    </span>
  );
}

function ProvenancePopover({ slot }: { slot: AdminProfileSlot }) {
  const { t } = useTranslation();
  const hash = slot.provenance.source_system_tree_hash;
  const orcaVersion = slot.provenance.orca_version;
  if (hash === null && orcaVersion === null) return null;
  const shortHash = hash ? hash.slice(0, SHORT_HASH_CHARS) : null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            className="size-6 text-muted-foreground"
            aria-label={t("modules.admin.profiles.provenance.open")}
          />
        }
      >
        <Info className="size-3.5" aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64 p-3 text-xs">
        <p className="mb-1 font-medium text-foreground">
          {t("modules.admin.profiles.provenance.label")}
        </p>
        {orcaVersion ? (
          <p className="text-muted-foreground">
            {t("modules.admin.profiles.provenance.orca_version")}:{" "}
            <span className="font-mono text-foreground">{orcaVersion}</span>
          </p>
        ) : null}
        {shortHash ? (
          <div className="mt-1 flex items-center gap-1 text-muted-foreground">
            <span>{t("modules.admin.profiles.provenance.tree_hash")}:</span>
            <span className="font-mono text-foreground">{shortHash}</span>
            <Button
              variant="ghost"
              size="icon"
              className="size-5"
              aria-label={t("modules.admin.profiles.provenance.copy")}
              onClick={() => {
                void navigator.clipboard?.writeText(hash ?? "");
              }}
            >
              <Copy className="size-3" aria-hidden="true" />
            </Button>
          </div>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** The reason copy for a non-offerable cell (AC-12), localized from the structured category. */
function CellReason({ slot }: { slot: AdminProfileSlot }) {
  const { t } = useTranslation();
  if (slot.offerable || slot.reason === null) return null;
  return (
    <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">
      {t(`modules.admin.profiles.reason.${slot.reason}`, {
        material: slot.material_class,
      })}
    </p>
  );
}

// Reason categories the import already shares with the 33.1 inventory vocabulary — reuse
// those localized strings (AC-19) rather than duplicating copy. Every other category gets a
// dedicated `import.error.*` string; an unknown/absent category falls back to `generic` so a
// rejected import ALWAYS surfaces a reason (admin fails closed/visible — AC-18).
const REUSED_REASON_CATEGORIES = new Set(["incompatible_for_material", "not_resolvable"]);
const IMPORT_ERROR_CATEGORIES = new Set([
  "invalid_partial",
  "unsupported_material_class",
  "missing_system_profile",
  "cli_validation_failed",
  "too_large",
]);

function rejectionMessageKey(category: string | null): string {
  if (category && REUSED_REASON_CATEGORIES.has(category)) {
    return `modules.admin.profiles.reason.${category}`;
  }
  if (category && IMPORT_ERROR_CATEGORIES.has(category)) {
    return `modules.admin.profiles.import.error.${category}`;
  }
  return "modules.admin.profiles.import.error.generic";
}

/**
 * Live "Import" affordance for compatible-but-not-imported cells (AC-16/AC-18).
 *
 * Renders ONLY on `not_imported` status, so incompatible cells (status `incompatible`) carry
 * no import action — unchanged from 33.1. A click opens the file picker; selecting a JSON
 * file posts it for `(printer_ref, material_class, quality_tier)` via `useImportProfile`. The
 * cell is NOT optimistically flipped to offerable — on success the hook invalidates
 * `["admin","profiles"]` and the grid refetches the server truth; on rejection the structured
 * `reason_category` is surfaced as a localized inline error.
 */
function ImportControl({ slot, printerRef }: { slot: AdminProfileSlot; printerRef: string }) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const importProfile = useImportProfile(printerRef);
  if (slot.status !== "not_imported") return null;

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-picking the same file after a rejection
    if (file) {
      importProfile.mutate({
        file,
        material_class: slot.material_class,
        quality_tier: slot.quality_tier,
      });
    }
  }

  return (
    <div className="mt-1 flex flex-col items-start gap-1">
      <input
        ref={inputRef}
        type="file"
        accept="application/json"
        className="sr-only"
        aria-label={t("modules.admin.profiles.import.choose_file")}
        onChange={onPick}
      />
      <Button
        variant="outline"
        size="sm"
        disabled={importProfile.isPending}
        className="h-6 px-2 text-[11px]"
        onClick={() => inputRef.current?.click()}
      >
        {importProfile.isPending
          ? t("modules.admin.profiles.import.importing")
          : t("modules.admin.profiles.import.action")}
      </Button>
      {importProfile.isError ? (
        <p className="text-[11px] leading-tight text-destructive" role="alert">
          {t(rejectionMessageKey(importRejectionCategory(importProfile.error)), {
            material: slot.material_class,
          })}
        </p>
      ) : null}
    </div>
  );
}

function CellBody({ slot, printerRef }: { slot: AdminProfileSlot; printerRef: string }) {
  return (
    <div className="flex flex-col items-start gap-0.5">
      <div className="flex items-center gap-1">
        <StatusBadge status={slot.status} />
        {slot.offerable ? <ProvenancePopover slot={slot} /> : null}
      </div>
      {slot.portal_label ? (
        <span className="text-[11px] text-foreground">{slot.portal_label}</span>
      ) : null}
      <CellReason slot={slot} />
      <ImportControl slot={slot} printerRef={printerRef} />
    </div>
  );
}

/**
 * Story 33.1 (AC-12) — the read-only admin profile inventory grid.
 *
 * Desktop: a 4x3 status matrix (rows = MATERIAL_CLASSES in resolve order, columns =
 * QUALITY_TIERS). Mobile: stacked per-material cards. Each cell carries exactly one status
 * by the backend precedence, plus a human-readable reason on every non-offerable cell.
 *
 * Story 33.2: `printerRef` is threaded to each cell so a compatible-not-imported cell can
 * post an import for `(printer_ref, material_class, quality_tier)` (AC-16).
 */
export function ProfileInventoryGrid({
  slots,
  printerRef,
}: {
  slots: AdminProfileSlot[];
  printerRef: string;
}) {
  const { t } = useTranslation();
  const byKey = new Map(
    slots.map((slot) => [`${slot.material_class}/${slot.quality_tier}`, slot]),
  );
  const slotFor = (material: string, tier: string) =>
    byKey.get(`${material}/${tier}`);

  return (
    <>
      {/* Desktop matrix */}
      <table className="hidden w-full border-collapse text-sm md:table">
        <thead>
          <tr>
            <th scope="col" className="p-2 text-left text-xs text-muted-foreground">
              {t("modules.admin.profiles.column_material")}
            </th>
            {QUALITY_TIERS.map((tier) => (
              <th
                key={tier}
                scope="col"
                className="p-2 text-left text-xs font-medium text-foreground"
              >
                {t(`modules.estimates.quality.${tier}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MATERIAL_CLASSES.map((material) => (
            <tr key={material} className="border-t border-border">
              <th
                scope="row"
                className="p-2 text-left align-top font-medium text-foreground"
              >
                {material}
              </th>
              {QUALITY_TIERS.map((tier) => {
                const slot = slotFor(material, tier);
                return (
                  <td key={tier} className="p-2 align-top">
                    {slot ? <CellBody slot={slot} printerRef={printerRef} /> : null}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile stacked cards */}
      <div className="flex flex-col gap-3 md:hidden">
        {MATERIAL_CLASSES.map((material) => (
          <div
            key={material}
            className="rounded-md border border-border bg-card p-3"
          >
            <p className="mb-2 font-medium text-card-foreground">{material}</p>
            <div className="flex flex-col gap-2">
              {QUALITY_TIERS.map((tier) => {
                const slot = slotFor(material, tier);
                return (
                  <div key={tier} className="flex items-start justify-between gap-2">
                    <span className="text-xs text-muted-foreground">
                      {t(`modules.estimates.quality.${tier}`)}
                    </span>
                    {slot ? <CellBody slot={slot} printerRef={printerRef} /> : null}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
