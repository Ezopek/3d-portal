import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Trash2,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { useId, useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";

import type {
  ProfileLibraryBlock,
  ProfileType,
  ProfileValidationState,
} from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { AdminTabs } from "@/modules/admin/AdminTabs";
import {
  libraryRejectionCategory,
  useDeleteProfileBlock,
} from "@/modules/admin/hooks/useDeleteProfileBlock";
import { useImportProfileBlock } from "@/modules/admin/hooks/useImportProfileBlock";
import { useProfileLibrary } from "@/modules/admin/hooks/useProfileLibrary";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";

// Validation-state → presentation. Reuses the 33.1 status-token set (success/warning/
// destructive) — no inline hex. State is NEVER conveyed by color alone: every badge carries
// icon + localized text (AC-18).
const STATE_PRESENTATION: Record<
  ProfileValidationState,
  { icon: LucideIcon; className: string }
> = {
  usable: { icon: CheckCircle2, className: "bg-success/10 text-success" },
  requires_attention: { icon: AlertTriangle, className: "bg-warning/10 text-warning" },
  error: { icon: XCircle, className: "bg-destructive/10 text-destructive" },
};

// Process FIRST (the slice is process-profiles-first). Drives both the filter chips and the
// default list order the backend already returns.
const PROFILE_TYPE_FILTERS: ProfileType[] = ["process", "filament", "machine"];

// Reason / rejection categories the FE localizes (admin sees WHY). An unknown category falls
// back to `generic` so a failure ALWAYS surfaces a reason (fails closed/visible).
const KNOWN_REASON_CATEGORIES = new Set([
  "unsupported_profile",
  "invalid_json",
  "too_large",
  "unknown_inherit_parent",
  "user_process_invalid_inheritance",
  "unknown_material_type",
  "not_found",
]);

function reasonKey(category: string | null): string {
  if (category && KNOWN_REASON_CATEGORIES.has(category)) {
    return `modules.admin.profileLibrary.reason.${category}`;
  }
  return "modules.admin.profileLibrary.reason.generic";
}

function StateBadge({ state }: { state: ProfileValidationState }) {
  const { t } = useTranslation();
  const { icon: Icon, className } = STATE_PRESENTATION[state];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium",
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden="true" />
      {t(`modules.admin.profileLibrary.validation.${state}`)}
    </span>
  );
}

/** The upload affordance: file picker + optional portal-label. Fails closed/visible (AC-16). */
function UploadControl() {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const labelId = useId();
  const [label, setLabel] = useState("");
  const importBlock = useImportProfileBlock();

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-picking the same file after a rejection
    if (file) {
      importBlock.mutate(
        { file, portal_label: label.trim() || undefined },
        { onSuccess: () => setLabel("") },
      );
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-card p-3">
      <div className="flex flex-wrap items-end gap-2">
        <div className="grid gap-1">
          <label htmlFor={labelId} className="text-xs font-medium text-foreground">
            {t("modules.admin.profileLibrary.upload.label_field")}
          </label>
          <input
            id={labelId}
            type="text"
            value={label}
            placeholder={t("modules.admin.profileLibrary.upload.label_placeholder")}
            className="rounded border border-border bg-background px-2 py-1 text-sm"
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/json"
          className="sr-only"
          aria-label={t("modules.admin.profileLibrary.upload.choose_file")}
          onChange={onPick}
        />
        <Button
          variant="default"
          size="sm"
          disabled={importBlock.isPending}
          onClick={() => inputRef.current?.click()}
        >
          {importBlock.isPending
            ? t("modules.admin.profileLibrary.upload.importing")
            : t("modules.admin.profileLibrary.upload.action")}
        </Button>
      </div>
      {importBlock.isError ? (
        <p className="text-xs leading-tight text-destructive" role="alert">
          {t(reasonKey(libraryRejectionCategory(importBlock.error)))}
        </p>
      ) : null}
    </div>
  );
}

/** Curated detail (NO raw Orca JSON, AC-16): inherit chain + flagged reasons + curated fields. */
function BlockDetail({ block }: { block: ProfileLibraryBlock }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-1.5 border-t border-border bg-muted/30 p-3 text-xs">
      <DetailRow label={t("modules.admin.profileLibrary.field.source")}>
        {block.source ?? "—"}
      </DetailRow>
      {block.settings_id ? (
        <DetailRow label={t("modules.admin.profileLibrary.field.settings_id")}>
          <span className="font-mono text-foreground">{block.settings_id}</span>
        </DetailRow>
      ) : null}
      {block.material_type ? (
        <DetailRow label={t("modules.admin.profileLibrary.field.material_type")}>
          <span className="font-mono text-foreground">{block.material_type}</span>
        </DetailRow>
      ) : null}
      <DetailRow label={t("modules.admin.profileLibrary.field.inherit_chain")}>
        {block.inherit_chain.length > 0 ? (
          <span className="font-mono text-foreground">{block.inherit_chain.join(" → ")}</span>
        ) : (
          "—"
        )}
      </DetailRow>
      {block.compatible_printers.length > 0 ? (
        <DetailRow label={t("modules.admin.profileLibrary.field.compatible_printers")}>
          <span className="font-mono text-foreground">
            {block.compatible_printers.join(", ")}
          </span>
        </DetailRow>
      ) : null}
      {block.reasons.length > 0 ? (
        <DetailRow label={t("modules.admin.profileLibrary.field.reasons")}>
          <ul className="flex flex-col gap-0.5">
            {block.reasons.map((reason) => (
              <li key={reason} className="text-warning">
                {t(reasonKey(reason))}
              </li>
            ))}
          </ul>
        </DetailRow>
      ) : null}
    </div>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap gap-1">
      <span className="text-muted-foreground">{label}:</span>
      <span className="text-foreground">{children}</span>
    </div>
  );
}

function BlockRow({
  block,
  onDelete,
}: {
  block: ProfileLibraryBlock;
  onDelete: (block: ProfileLibraryBlock) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ChevronIcon = open ? ChevronDown : ChevronRight;
  return (
    <li className="rounded-md border border-border bg-card">
      <div className="flex items-center gap-2 p-2">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-expanded={open}
          aria-label={t(
            open
              ? "modules.admin.profileLibrary.detail.hide"
              : "modules.admin.profileLibrary.detail.show",
          )}
          onClick={() => setOpen((v) => !v)}
        >
          <ChevronIcon className="size-4" aria-hidden="true" />
        </Button>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate font-medium text-foreground">{block.name}</span>
          {block.portal_label ? (
            <span className="truncate text-xs text-muted-foreground">{block.portal_label}</span>
          ) : null}
        </div>
        <StateBadge state={block.validation_state} />
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-destructive"
          aria-label={t("modules.admin.profileLibrary.delete.action", { name: block.name })}
          onClick={() => onDelete(block)}
        >
          <Trash2 className="size-4" aria-hidden="true" />
        </Button>
      </div>
      {open ? <BlockDetail block={block} /> : null}
    </li>
  );
}

/**
 * PROFILE-LIB-1 (AC-16) — the operator profile-block inventory surface.
 *
 * A minimal admin CRUD: upload, a type-filtered list (process first) grouped by type with a
 * validation-state badge, a per-row curated detail expander (inherit chain + flagged reasons —
 * NO raw Orca JSON anywhere), and a delete behind a confirm dialog. Fails closed/visible on a
 * load error (admin discipline); never fabricates success.
 */
export function ProfileLibraryPage() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<ProfileType | undefined>(undefined);
  const library = useProfileLibrary(filter);
  const deleteBlock = useDeleteProfileBlock();
  const [confirmTarget, setConfirmTarget] = useState<ProfileLibraryBlock | null>(null);

  function handleDeleteConfirm() {
    if (!confirmTarget) return;
    deleteBlock.mutate(confirmTarget.block_id, {
      onSuccess: () => setConfirmTarget(null),
      onSettled: () => setConfirmTarget(null),
    });
  }

  const blocks = library.data?.blocks ?? [];
  const byType = PROFILE_TYPE_FILTERS.map((type) => ({
    type,
    items: blocks.filter((b) => b.profile_type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="profile-library" />

      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">
          {t("modules.admin.profileLibrary.title")}
        </h1>
        <p className="text-xs text-muted-foreground">
          {t("modules.admin.profileLibrary.description")}
        </p>
      </header>

      <UploadControl />

      <div className="flex flex-wrap gap-2" role="group" aria-label={t("modules.admin.profileLibrary.filter.all")}>
        <FilterChip active={filter === undefined} onClick={() => setFilter(undefined)}>
          {t("modules.admin.profileLibrary.filter.all")}
        </FilterChip>
        {PROFILE_TYPE_FILTERS.map((type) => (
          <FilterChip key={type} active={filter === type} onClick={() => setFilter(type)}>
            {t(`modules.admin.profileLibrary.filter.${type}`)}
          </FilterChip>
        ))}
      </div>

      {library.isError ? (
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.profileLibrary.error_title")}
          </p>
          <Button variant="outline" size="sm" onClick={() => void library.refetch()}>
            {t("modules.admin.profileLibrary.retry")}
          </Button>
        </div>
      ) : library.isLoading ? (
        <div className="flex flex-col gap-2" aria-hidden="true" data-testid="library-skeleton">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      ) : byType.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {t("modules.admin.profileLibrary.empty")}
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {byType.map((group) => (
            <section key={group.type} className="flex flex-col gap-2">
              <h2 className="text-sm font-medium text-foreground">
                {t(`modules.admin.profileLibrary.filter.${group.type}`)}
              </h2>
              <ul className="flex flex-col gap-2">
                {group.items.map((block) => (
                  <BlockRow key={block.block_id} block={block} onDelete={setConfirmTarget} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={confirmTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmTarget(null);
        }}
        title={t("modules.admin.profileLibrary.delete.confirm_title", {
          name: confirmTarget?.name ?? "",
        })}
        description={t("modules.admin.profileLibrary.delete.confirm_description")}
        destructive
        pending={deleteBlock.isPending}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
        active
          ? "border-primary bg-primary/10 text-foreground"
          : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}
