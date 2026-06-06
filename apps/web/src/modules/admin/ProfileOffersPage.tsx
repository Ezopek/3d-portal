import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Pencil,
  Trash2,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type {
  MaterialClass,
  OfferValidationState,
  OfferVisibility,
  PrintProfileOffer,
  ProfileLibraryBlock,
  ProfileOffersFilters,
  ProfileType,
} from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { AdminTabs } from "@/modules/admin/AdminTabs";
import {
  offerRejectionCategory,
  useCreateProfileOffer,
} from "@/modules/admin/hooks/useCreateProfileOffer";
import { useDeleteProfileOffer } from "@/modules/admin/hooks/useDeleteProfileOffer";
import { useProfileLibrary } from "@/modules/admin/hooks/useProfileLibrary";
import { useProfileOffers } from "@/modules/admin/hooks/useProfileOffers";
import { useUpdateProfileOffer } from "@/modules/admin/hooks/useUpdateProfileOffer";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";

// Validation-state → presentation. Reuses the shipped status-token set (success/warning/
// destructive) — no inline hex. State is NEVER conveyed by color alone: every badge carries
// icon + localized text (AC-17, WCAG 1.4.1). Library uses `error` where offers use `invalid`.
const STATE_PRESENTATION: Record<
  OfferValidationState,
  { icon: LucideIcon; className: string }
> = {
  usable: { icon: CheckCircle2, className: "bg-success/10 text-success" },
  requires_attention: { icon: AlertTriangle, className: "bg-warning/10 text-warning" },
  invalid: { icon: XCircle, className: "bg-destructive/10 text-destructive" },
};

// The generic material-category table (SCP § 3.6). Rendered as DATA (untranslated — no
// per-material i18n key), matching the backend `OFFER_MATERIAL_CATEGORIES` set.
const MATERIAL_CATEGORIES: readonly MaterialClass[] = ["PLA", "PETG", "PCTG", "TPU"];

// The three chain slots, in machine→process→filament order (the picker + trio + detail order).
const CHAIN_SLOTS: readonly ProfileType[] = ["machine", "process", "filament"];

// Reason / rejection categories the FE localizes (admin sees WHY). An unknown category falls
// back to `generic` so a failure ALWAYS surfaces a reason (fails closed/visible). Covers the 8
// backend validation reasons (AC-4) + the endpoint rejection categories (AC-9/AC-12).
const KNOWN_REASON_CATEGORIES = new Set([
  "unknown_block",
  "wrong_block_type",
  "block_unusable",
  "block_requires_attention",
  "filament_machine_incompatible",
  "material_category_mismatch",
  "default_but_hidden",
  "duplicate_default",
  "invalid_chain",
  "unsupported_material_category",
  "invalid_offer",
  "invalid_json",
  "too_large",
  "not_found",
]);

function reasonKey(category: string | null): string {
  if (category && KNOWN_REASON_CATEGORIES.has(category)) {
    return `modules.admin.profileOffers.reason.${category}`;
  }
  return "modules.admin.profileOffers.reason.generic";
}

function blockForSlot(
  offer: PrintProfileOffer,
  slot: ProfileType,
): ProfileLibraryBlock | undefined {
  return offer.chain_blocks.find((b) => b.profile_type === slot);
}

function StateBadge({ state }: { state: OfferValidationState }) {
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
      {t(`modules.admin.profileOffers.validation.${state}`)}
    </span>
  );
}

/** A small text-labelled chip — visibility + default indicators on a row. */
function MetaChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded border border-border px-1.5 py-0.5 text-xs text-muted-foreground">
      {children}
    </span>
  );
}

interface OfferFormState {
  machine_block_id: string;
  process_block_id: string;
  filament_block_id: string;
  label: string;
  description: string;
  visibility: OfferVisibility;
  is_default: boolean;
  categories: MaterialClass[];
}

function emptyFormState(): OfferFormState {
  return {
    machine_block_id: "",
    process_block_id: "",
    filament_block_id: "",
    label: "",
    description: "",
    visibility: "hidden",
    is_default: false,
    categories: [],
  };
}

function formStateFromOffer(offer: PrintProfileOffer): OfferFormState {
  return {
    machine_block_id: offer.chain.machine_block_id,
    process_block_id: offer.chain.process_block_id,
    filament_block_id: offer.chain.filament_block_id,
    label: offer.label,
    description: offer.description ?? "",
    visibility: offer.visibility,
    is_default: offer.is_default,
    categories: offer.compatible_material_categories.filter((c): c is MaterialClass =>
      (MATERIAL_CATEGORIES as readonly string[]).includes(c),
    ),
  };
}

/**
 * Compose (create) or edit an offer. The three slot pickers are single-select native `<select>`s
 * over the library (the UX-endorsed lower-effort floor — NOT an N×M matrix). On EDIT the chain
 * pickers are read-only (the chain is immutable on PATCH, AC-12) with a "delete + re-create"
 * hint; label/visibility/default/categories stay editable. Fails closed/visible: a create/edit
 * rejection surfaces the structured reason inline; nothing is silently stored.
 */
function OfferForm({
  mode,
  offer,
  libraryBlocks,
  onClose,
}: {
  mode: "create" | "edit";
  offer?: PrintProfileOffer;
  libraryBlocks: ProfileLibraryBlock[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const fieldId = useId();
  const [form, setForm] = useState<OfferFormState>(() =>
    mode === "edit" && offer ? formStateFromOffer(offer) : emptyFormState(),
  );
  const create = useCreateProfileOffer();
  const update = useUpdateProfileOffer();
  const pending = create.isPending || update.isPending;
  const rejection = create.error ?? update.error;

  const blocksByType = useMemo(() => {
    const grouped: Record<ProfileType, ProfileLibraryBlock[]> = {
      machine: [],
      process: [],
      filament: [],
    };
    for (const block of libraryBlocks) grouped[block.profile_type].push(block);
    return grouped;
  }, [libraryBlocks]);

  const chainComplete =
    form.machine_block_id !== "" &&
    form.process_block_id !== "" &&
    form.filament_block_id !== "";
  const canSave = form.label.trim() !== "" && (mode === "edit" || chainComplete);

  function toggleCategory(category: MaterialClass) {
    setForm((prev) => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter((c) => c !== category)
        : [...prev.categories, category],
    }));
  }

  function handleSave() {
    const description = form.description.trim() === "" ? null : form.description.trim();
    if (mode === "edit" && offer) {
      update.mutate(
        {
          offerId: offer.offer_id,
          patch: {
            label: form.label.trim(),
            description,
            visibility: form.visibility,
            is_default: form.is_default,
            compatible_material_categories: form.categories,
          },
        },
        { onSuccess: onClose },
      );
      return;
    }
    create.mutate(
      {
        label: form.label.trim(),
        description,
        chain: {
          machine_block_id: form.machine_block_id,
          process_block_id: form.process_block_id,
          filament_block_id: form.filament_block_id,
        },
        visibility: form.visibility,
        is_default: form.is_default,
        compatible_material_categories: form.categories,
      },
      { onSuccess: onClose },
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <h2 className="text-sm font-semibold text-foreground">
        {t(
          mode === "edit"
            ? "modules.admin.profileOffers.form.edit_title"
            : "modules.admin.profileOffers.form.compose_title",
        )}
      </h2>

      {/* The three single-select slot pickers (machine / process / filament). */}
      <div className="grid gap-2">
        {CHAIN_SLOTS.map((slot) => {
          const key = `${slot}_block_id` as const;
          const selectId = `${fieldId}-${slot}`;
          const selected = blockForSlotValue(form, slot);
          const selectedBlock = libraryBlocks.find((b) => b.block_id === selected);
          return (
            <div key={slot} className="grid gap-1">
              <label htmlFor={selectId} className="text-xs font-medium text-foreground">
                {t(`modules.admin.profileOffers.form.slot.${slot}`)}
              </label>
              {mode === "edit" ? (
                <span
                  id={selectId}
                  className="rounded border border-border bg-muted/40 px-2 py-1 text-sm text-foreground"
                >
                  {selectedBlock?.name ?? "—"}
                </span>
              ) : (
                <select
                  id={selectId}
                  value={selected}
                  className="rounded border border-border bg-background px-2 py-1 text-sm"
                  onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                >
                  <option value="">
                    {t("modules.admin.profileOffers.form.slot_placeholder")}
                  </option>
                  {blocksByType[slot].map((block) => (
                    <option key={block.block_id} value={block.block_id}>
                      {block.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          );
        })}
        {mode === "edit" ? (
          <p className="text-xs text-muted-foreground">
            {t("modules.admin.profileOffers.form.chain_immutable_hint")}
          </p>
        ) : null}
      </div>

      {/* Label + description (DATA — untranslated). */}
      <div className="grid gap-1">
        <label htmlFor={`${fieldId}-label`} className="text-xs font-medium text-foreground">
          {t("modules.admin.profileOffers.form.label_field")}
        </label>
        <input
          id={`${fieldId}-label`}
          type="text"
          value={form.label}
          placeholder={t("modules.admin.profileOffers.form.label_placeholder")}
          className="rounded border border-border bg-background px-2 py-1 text-sm"
          onChange={(e) => setForm((prev) => ({ ...prev, label: e.target.value }))}
        />
      </div>
      <div className="grid gap-1">
        <label htmlFor={`${fieldId}-desc`} className="text-xs font-medium text-foreground">
          {t("modules.admin.profileOffers.form.description_field")}
        </label>
        <input
          id={`${fieldId}-desc`}
          type="text"
          value={form.description}
          className="rounded border border-border bg-background px-2 py-1 text-sm"
          onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
        />
      </div>

      {/* Visibility (two-state) + default (with the attention-rule helper). */}
      <div className="flex flex-wrap items-start gap-4">
        <div className="grid gap-1">
          <span className="text-xs font-medium text-foreground">
            {t("modules.admin.profileOffers.form.visibility")}
          </span>
          <div className="flex gap-1" role="group" aria-label={t("modules.admin.profileOffers.form.visibility")}>
            {(["hidden", "visible"] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={form.visibility === value}
                onClick={() => setForm((prev) => ({ ...prev, visibility: value }))}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  form.visibility === value
                    ? "border-primary bg-primary/10 text-foreground"
                    : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {t(`modules.admin.profileOffers.visibility.${value}`)}
              </button>
            ))}
          </div>
        </div>
        <div className="grid gap-1">
          <span className="text-xs font-medium text-foreground">
            {t("modules.admin.profileOffers.form.default")}
          </span>
          <button
            type="button"
            aria-pressed={form.is_default}
            onClick={() => setForm((prev) => ({ ...prev, is_default: !prev.is_default }))}
            className={cn(
              "w-fit rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              form.is_default
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {t(`modules.admin.profileOffers.form.default_${form.is_default ? "on" : "off"}`)}
          </button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        {t("modules.admin.profileOffers.form.default_helper")}
      </p>

      {/* Material categories (multi-select chips, DATA values). */}
      <div className="grid gap-1">
        <span className="text-xs font-medium text-foreground">
          {t("modules.admin.profileOffers.form.categories")}
        </span>
        <div className="flex flex-wrap gap-1" role="group" aria-label={t("modules.admin.profileOffers.form.categories")}>
          {MATERIAL_CATEGORIES.map((category) => (
            <button
              key={category}
              type="button"
              aria-pressed={form.categories.includes(category)}
              onClick={() => toggleCategory(category)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                form.categories.includes(category)
                  ? "border-primary bg-primary/10 text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {rejection ? (
        <p className="text-xs leading-tight text-destructive" role="alert">
          {t(reasonKey(offerRejectionCategory(rejection)))}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button variant="default" size="sm" disabled={pending || !canSave} onClick={handleSave}>
          {pending
            ? t("modules.admin.profileOffers.form.saving")
            : t("modules.admin.profileOffers.form.save")}
        </Button>
        <Button variant="outline" size="sm" disabled={pending} onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}

function blockForSlotValue(form: OfferFormState, slot: ProfileType): string {
  if (slot === "machine") return form.machine_block_id;
  if (slot === "process") return form.process_block_id;
  return form.filament_block_id;
}

/** Curated detail (NO raw Orca JSON, AC-17): chain blocks + full flagged-reason list. */
function OfferDetail({ offer }: { offer: PrintProfileOffer }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-2 border-t border-border bg-muted/30 p-3 text-xs">
      {CHAIN_SLOTS.map((slot) => {
        const block = blockForSlot(offer, slot);
        return (
          <div key={slot} className="flex flex-col gap-0.5">
            <span className="font-medium text-foreground">
              {t(`modules.admin.profileOffers.form.slot.${slot}`)}
            </span>
            {block ? (
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 pl-2 text-muted-foreground">
                <span className="text-foreground">{block.name}</span>
                {block.material_type ? (
                  <span>
                    {t("modules.admin.profileOffers.field.material_type")}:{" "}
                    <span className="font-mono text-foreground">{block.material_type}</span>
                  </span>
                ) : null}
                {block.inherit_chain.length > 0 ? (
                  <span>
                    {t("modules.admin.profileOffers.field.inherit_chain")}:{" "}
                    <span className="font-mono text-foreground">
                      {block.inherit_chain.join(" → ")}
                    </span>
                  </span>
                ) : null}
                {block.compatible_printers.length > 0 ? (
                  <span>
                    {t("modules.admin.profileOffers.field.compatible_printers")}:{" "}
                    <span className="font-mono text-foreground">
                      {block.compatible_printers.join(", ")}
                    </span>
                  </span>
                ) : null}
              </div>
            ) : (
              <span className="pl-2 text-muted-foreground">
                {t("modules.admin.profileOffers.field.block_missing")}
              </span>
            )}
          </div>
        );
      })}
      {offer.reasons.length > 0 ? (
        <div className="flex flex-col gap-0.5">
          <span className="font-medium text-foreground">
            {t("modules.admin.profileOffers.field.reasons")}
          </span>
          <ul className="flex flex-col gap-0.5 pl-2">
            {offer.reasons.map((reason) => (
              <li key={reason} className="text-warning">
                {t(reasonKey(reason))}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function OfferRow({
  offer,
  onEdit,
  onDelete,
}: {
  offer: PrintProfileOffer;
  onEdit: (offer: PrintProfileOffer) => void;
  onDelete: (offer: PrintProfileOffer) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ChevronIcon = open ? ChevronDown : ChevronRight;
  const firstReason = offer.reasons[0];
  const trio = CHAIN_SLOTS.map((slot) => blockForSlot(offer, slot)?.name ?? "—").join(" · ");

  return (
    <li className="rounded-md border border-border bg-card">
      <div className="flex items-center gap-2 p-2">
        <Button
          variant="ghost"
          size="icon-sm"
          aria-expanded={open}
          aria-label={t(
            open
              ? "modules.admin.profileOffers.detail.hide"
              : "modules.admin.profileOffers.detail.show",
          )}
          onClick={() => setOpen((v) => !v)}
        >
          <ChevronIcon className="size-4" aria-hidden="true" />
        </Button>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate font-medium text-foreground">{offer.label}</span>
          <span className="truncate text-xs text-muted-foreground">{trio}</span>
          {offer.validation_state === "invalid" && firstReason ? (
            <span className="truncate text-xs text-destructive">{t(reasonKey(firstReason))}</span>
          ) : null}
          <div className="mt-0.5 flex flex-wrap gap-1">
            <MetaChip>{t(`modules.admin.profileOffers.visibility.${offer.visibility}`)}</MetaChip>
            {offer.is_default ? (
              <MetaChip>{t("modules.admin.profileOffers.badge.default")}</MetaChip>
            ) : null}
          </div>
        </div>
        <StateBadge state={offer.validation_state} />
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={t("modules.admin.profileOffers.edit.action", { label: offer.label })}
          onClick={() => onEdit(offer)}
        >
          <Pencil className="size-4" aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-destructive"
          aria-label={t("modules.admin.profileOffers.delete.action", { label: offer.label })}
          onClick={() => onDelete(offer)}
        >
          <Trash2 className="size-4" aria-hidden="true" />
        </Button>
      </div>
      {open ? <OfferDetail offer={offer} /> : null}
    </li>
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

/**
 * PROFILE-OFFER-1 (AC-17) — the admin PrintProfileOffer composition surface.
 *
 * A minimal admin CRUD over the shipped profile-block library: compose an offer from exactly
 * three single-select pickers (machine / process / filament) + label/visibility/default/
 * material-categories, list offers with a validation-state badge, a curated detail expander (NO
 * raw Orca JSON anywhere), edit label/visibility/default/categories (chain immutable), and
 * delete behind a confirm. Validation is recomputed server-side at read time (`staleTime: 0`),
 * so the badge is live truth, never a create-time snapshot. Fails closed/visible on a load
 * error; never fabricates offers.
 */
export function ProfileOffersPage() {
  const { t } = useTranslation();
  const [materialFilter, setMaterialFilter] = useState<MaterialClass | undefined>(undefined);
  const [visibilityFilter, setVisibilityFilter] = useState<OfferVisibility | undefined>(undefined);
  const filters: ProfileOffersFilters | undefined =
    materialFilter || visibilityFilter
      ? { material_category: materialFilter, visibility: visibilityFilter }
      : undefined;

  const offers = useProfileOffers(filters);
  const library = useProfileLibrary();
  const deleteOffer = useDeleteProfileOffer();

  const [formMode, setFormMode] = useState<
    { kind: "create" } | { kind: "edit"; offer: PrintProfileOffer } | null
  >(null);
  const [confirmTarget, setConfirmTarget] = useState<PrintProfileOffer | null>(null);

  const libraryBlocks = library.data?.blocks ?? [];
  const items = offers.data?.offers ?? [];

  function handleDeleteConfirm() {
    if (!confirmTarget) return;
    deleteOffer.mutate(confirmTarget.offer_id, {
      onSettled: () => setConfirmTarget(null),
    });
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <AdminTabs activeTab="profile-offers" />

      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold text-foreground">
          {t("modules.admin.profileOffers.title")}
        </h1>
        <p className="text-xs text-muted-foreground">
          {t("modules.admin.profileOffers.description")}
        </p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-col gap-2">
          <div
            className="flex flex-wrap gap-1"
            role="group"
            aria-label={t("modules.admin.profileOffers.filter.material")}
          >
            <FilterChip active={!materialFilter} onClick={() => setMaterialFilter(undefined)}>
              {t("modules.admin.profileOffers.filter.all")}
            </FilterChip>
            {MATERIAL_CATEGORIES.map((category) => (
              <FilterChip
                key={category}
                active={materialFilter === category}
                onClick={() => setMaterialFilter(category)}
              >
                {category}
              </FilterChip>
            ))}
          </div>
          <div
            className="flex flex-wrap gap-1"
            role="group"
            aria-label={t("modules.admin.profileOffers.filter.visibility")}
          >
            <FilterChip active={!visibilityFilter} onClick={() => setVisibilityFilter(undefined)}>
              {t("modules.admin.profileOffers.filter.all")}
            </FilterChip>
            {(["visible", "hidden"] as const).map((value) => (
              <FilterChip
                key={value}
                active={visibilityFilter === value}
                onClick={() => setVisibilityFilter(value)}
              >
                {t(`modules.admin.profileOffers.visibility.${value}`)}
              </FilterChip>
            ))}
          </div>
        </div>
        <Button
          variant="default"
          size="sm"
          disabled={formMode?.kind === "create"}
          onClick={() => setFormMode({ kind: "create" })}
        >
          {t("modules.admin.profileOffers.compose.action")}
        </Button>
      </div>

      {formMode ? (
        <OfferForm
          mode={formMode.kind}
          offer={formMode.kind === "edit" ? formMode.offer : undefined}
          libraryBlocks={libraryBlocks}
          onClose={() => setFormMode(null)}
        />
      ) : null}

      {offers.isError ? (
        <div className="flex flex-col items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-4">
          <p className="text-sm font-medium text-destructive">
            {t("modules.admin.profileOffers.error_title")}
          </p>
          <Button variant="outline" size="sm" onClick={() => void offers.refetch()}>
            {t("modules.admin.profileOffers.retry")}
          </Button>
        </div>
      ) : offers.isLoading ? (
        <div className="flex flex-col gap-2" aria-hidden="true" data-testid="offers-skeleton">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("modules.admin.profileOffers.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((offer) => (
            <OfferRow
              key={offer.offer_id}
              offer={offer}
              onEdit={(o) => setFormMode({ kind: "edit", offer: o })}
              onDelete={setConfirmTarget}
            />
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={confirmTarget !== null}
        onOpenChange={(next) => {
          if (!next) setConfirmTarget(null);
        }}
        title={t("modules.admin.profileOffers.delete.confirm_title", {
          label: confirmTarget?.label ?? "",
        })}
        description={t("modules.admin.profileOffers.delete.confirm_description")}
        destructive
        pending={deleteOffer.isPending}
        onConfirm={handleDeleteConfirm}
      />
    </div>
  );
}
