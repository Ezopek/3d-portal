import { Box, ChevronDown, ChevronRight, Download, Package, Trash2, Upload } from "lucide-react";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import type { ModelFileKind, ModelFileRead } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { useDeleteFile } from "@/modules/catalog/hooks/mutations/useDeleteFile";
import { useSetFileRenderSelection } from "@/modules/catalog/hooks/mutations/useSetFileRenderSelection";
import { useTriggerRender } from "@/modules/catalog/hooks/mutations/useTriggerRender";
import { useUploadFile } from "@/modules/catalog/hooks/mutations/useUploadFile";
import {
  Viewer3DInline,
  Viewer3DModal,
  type StlFile,
} from "@/modules/catalog/components/viewer3d";
import { useFileIndex } from "@/modules/catalog/components/viewer3d/hooks/useFileIndex";
import { CatalogEstimateProfileSelector } from "@/modules/estimates/components/CatalogEstimateProfileSelector";
import { EstimateChip } from "@/modules/estimates/components/EstimateChip";
import { PublishedOfferPicker } from "@/modules/estimates/components/PublishedOfferPicker";
import { RowEstimatePanel } from "@/modules/estimates/components/RowEstimatePanel";
import { usePublishedOffers } from "@/modules/estimates/hooks/usePublishedOffers";
import { useQualityTierAvailability } from "@/modules/estimates/hooks/useQualityTierAvailability";
import {
  CATALOG_ESTIMATE_PRINTER_REF,
  defaultPreset,
  type PrintIntentPresetInput,
} from "@/modules/estimates/lib/preset";
import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";

type Visible = "stl" | "source" | "archive_3mf";

const CHIPS: { kind: Visible; label: string }[] = [
  { kind: "stl", label: "STL" },
  { kind: "source", label: "Source" },
  { kind: "archive_3mf", label: "3MF" },
];

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isVisible(kind: ModelFileKind): kind is Visible {
  return kind === "stl" || kind === "source" || kind === "archive_3mf";
}

export function FilesTab({
  modelId,
  files,
}: {
  modelId: string;
  files: readonly ModelFileRead[];
}) {
  const { t } = useTranslation();
  const [active, setActive] = useState<Visible>("stl");
  const { isAdmin, isAuthenticated } = useAuth();
  const setRenderSelection = useSetFileRenderSelection(modelId);
  const triggerRender = useTriggerRender(modelId);
  const deleteFile = useDeleteFile(modelId);
  const upload = useUploadFile(modelId);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // EST-DISPLAY-1 — one GLOBAL, member-visible estimate preset feeds every STL row chip AND
  // the expanded panel (UX §A; not per-row). Ephemeral component state (UX Q1 v1 default —
  // resets on navigate; no persistence). Defaults to PLA · standard · no pin, the exact
  // EST-INGEST-1 default bundle, so the first-load chip shows real numbers, not `absent`.
  const [preset, setPreset] = useState<PrintIntentPresetInput>(defaultPreset);

  // Story 36.3 (AC-6) — ephemeral offer selection; null = preset mode (§D.3).
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const tierAvailability = useQualityTierAvailability(
    preset.material_class,
    CATALOG_ESTIMATE_PRINTER_REF,
  );
  // Pass `undefined` until the availability read resolves (and on error) so the selector
  // fails open visually — every compatible tier stays selectable rather than locking out
  // Standard while the (5-min-cached) availability query is in flight or has failed. Once
  // resolved, the array disables only the tiers the backend reports as unresolvable.
  const catalogTierAvailability = tierAvailability.data?.tiers;
  const selectedTierAvailability = catalogTierAvailability?.find(
    (tier) => tier.quality_tier === preset.quality_tier,
  );
  // NFR21-NO-422-1: UI fail-open must NOT mean request fail-open. Estimate reads are held
  // until the backend availability response for the CURRENT material confirms the selected
  // tier is offerable. This closes the material-switch race (e.g. PLA → TPU/standard before
  // TPU availability arrives) that could otherwise fire a member-reachable resolver 422.
  const canReadSelectedEstimate =
    tierAvailability.isSuccess && selectedTierAvailability?.available === true;

  // Story 36.3 (AC-2/AC-9) — published offers for the current material.
  // Enabled only when authenticated and there are STL files (§E.6, §D.5).
  const publishedOffers = usePublishedOffers(preset.material_class, {
    isAuthenticated: isAuthenticated === true,
    hasStlFiles: active === "stl",
  });

  // AC-9: when the offer list settles and no longer contains the selected offer,
  // deselect (material changed or offer was unpublished). useEffect to avoid
  // side-effects during render.
  useEffect(() => {
    if (selectedOfferId === null || !publishedOffers.isSuccess) return;
    const ids = new Set(publishedOffers.data.offers.map((o) => o.offer_id));
    if (!ids.has(selectedOfferId)) setSelectedOfferId(null);
  }, [publishedOffers.isSuccess, publishedOffers.data, selectedOfferId]);

  const stlFiles: StlFile[] = useMemo(
    () =>
      files
        .filter((f) => f.kind === "stl")
        .map((f) => ({
          id: f.id,
          modelId,
          name: f.original_name,
          size: f.size_bytes,
        })),
    [files, modelId],
  );
  const stlIndex = useFileIndex(stlFiles);
  const stlById = useMemo(() => {
    const m = new Map<string, StlFile>();
    for (const f of stlFiles) m.set(f.id, f);
    return m;
  }, [stlFiles]);

  const counts = new Map<Visible, number>();
  for (const f of files) {
    if (isVisible(f.kind)) counts.set(f.kind, (counts.get(f.kind) ?? 0) + 1);
  }
  const visible = files.filter((f) => f.kind === active);
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalInitialId, setModalInitialId] = useState<string | undefined>(
    undefined,
  );

  // Initiative 10 Story 16.6 — total printable count for the "Download all" CTA.
  const printableTotal =
    (counts.get("stl") ?? 0) + (counts.get("source") ?? 0) + (counts.get("archive_3mf") ?? 0);

  return (
    <div className="space-y-3 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          {CHIPS.map((c) => (
            <button
              key={c.kind}
              type="button"
              onClick={() => setActive(c.kind)}
              className={cn(
                "rounded px-3 py-1 text-xs",
                c.kind === active
                  ? "bg-primary/10 text-foreground font-medium ring-1 ring-inset ring-primary"
                  : "bg-muted text-muted-foreground hover:text-foreground",
              )}
            >
              {c.label} · {counts.get(c.kind) ?? 0}
            </button>
          ))}
        </div>
        {printableTotal > 0 && (
          <a
            href={`/api/models/${modelId}/bundle`}
            className="inline-flex items-center gap-1.5 rounded border border-border bg-card px-3 py-1 text-xs font-medium text-foreground hover:bg-accent"
            aria-label={t("catalog.actions.download_all")}
          >
            <Package className="size-3.5" aria-hidden />
            <span>{t("catalog.actions.download_all")}</span>
            <span className="text-muted-foreground">({printableTotal})</span>
          </a>
        )}
      </div>

      {modalOpen && (
        <Suspense fallback={null}>
          <Viewer3DModal
            files={stlFiles}
            initialFileId={modalInitialId}
            onClose={() => setModalOpen(false)}
          />
        </Suspense>
      )}

      {isAdmin && (
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="sr-only"
            onChange={(e) => {
              const files = Array.from(e.currentTarget.files ?? []);
              for (const f of files) {
                upload.mutate(
                  { file: f, kind: active },
                  {
                    onError: (err) => toast.error(err.message),
                  },
                );
              }
              e.currentTarget.value = "";
            }}
          />
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={upload.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mr-1 size-3.5" aria-hidden />
            {upload.isPending
              ? t("catalog.actions.uploading")
              : t("catalog.actions.upload_files", { kind: active.toUpperCase() })}
          </Button>
        </div>
      )}

      {/* EST-DISPLAY-1 (UX §A; product correction) — compact, member-visible estimate process /
          quality profile selector, visually subordinate to the STL list. This surface is an
          orientational per-STL gram ESTIMATE preview only: material class + Spoolman pin are NOT
          exposed here (they stay at the EST-INGEST-1 internal defaults so the chip/panel query
          keys are unchanged). Read-only: it re-keys which estimate every chip/panel reads; it
          never enqueues, recomputes, or exposes ordering / spool semantics. Separate from the
          admin render controls below.
          Story 36.4: PublishedOfferPicker is passed as children so that the offer select
          appears as a third inline item in the same flex row (one compact estimate profile bar). */}
      {active === "stl" && stlFiles.length > 0 && (
        <CatalogEstimateProfileSelector
          value={preset}
          onChange={setPreset}
          availability={catalogTierAvailability}
        >
          {isAuthenticated && (
            <PublishedOfferPicker
              offers={publishedOffers.data?.offers ?? (publishedOffers.isSuccess ? [] : null)}
              selectedOfferId={selectedOfferId}
              onSelect={setSelectedOfferId}
              isLoading={publishedOffers.isPending}
              isError={publishedOffers.isError}
              onRetry={() => void publishedOffers.refetch()}
              isAuthenticated={isAuthenticated}
            />
          )}
        </CatalogEstimateProfileSelector>
      )}

      {isAdmin && active === "stl" && visible.length > 0 && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {t("catalog.actions.checkedHelp")}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={triggerRender.isPending || setRenderSelection.isPending}
            onClick={() =>
              triggerRender.mutate(
                { selected_stl_file_ids: [] },
                {
                  onSuccess: () => toast.success("Render queued"),
                  onError: (e) => toast.error(e.message),
                },
              )
            }
          >
            {triggerRender.isPending
              ? t("catalog.actions.queueing")
              : t("catalog.actions.rerenderPreview")}
          </Button>
        </div>
      )}
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("catalog.empty.files")}</p>
      ) : (
        <ul className="divide-y divide-border rounded border border-border">
          {visible.map((f) => {
            const isStl = f.kind === "stl";
            const isExpanded = isStl && expandedFileId === f.id;
            const stlFile = stlById.get(f.id);
            return (
              <li key={f.id} className="text-sm">
                {/* Mobile (UX §Mobile notes): filename on its own line, metadata
                    (chip · size · preview · download) reflows to a second line so the
                    filename never truncates to zero width. On sm+ the metadata group
                    becomes `display:contents` and the row collapses back to one line. */}
                <div className="flex flex-col gap-1 p-2 sm:flex-row sm:items-center sm:gap-3">
                  <div className="flex min-w-0 items-center gap-3 sm:flex-1">
                    {isAdmin && isStl && (
                      <input
                        type="checkbox"
                        aria-label={`include ${f.original_name} in renders`}
                        checked={f.selected_for_render}
                        disabled={setRenderSelection.isPending}
                        onChange={(e) =>
                          setRenderSelection.mutate({
                            fileId: f.id,
                            selected: e.currentTarget.checked,
                          })
                        }
                      />
                    )}
                    {isStl && (
                      <span className="w-6 shrink-0 font-mono text-xs text-muted-foreground">
                        {stlIndex.positionOf(f.id)}
                      </span>
                    )}
                    {/* Drop the redundant `stl` kind label inside the STL-filtered tab
                        (UX §B); keep it for source/3mf rows. */}
                    {!isStl && (
                      <span className="font-mono text-xs">{f.kind}</span>
                    )}
                    <span className="min-w-0 flex-1 truncate">
                      {f.original_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 sm:contents">
                    {/* EST-DISPLAY-1 (UX §B) — inline grams-only chip in a fixed scan
                        column so grams align vertically down the list; the chip never
                        truncates. Keyed by `f.sha256` (the stl_hash); empty ⇒ no request. */}
                    {isStl && (
                      <div className="flex w-20 shrink-0 justify-end">
                        <EstimateChip
                          stlHash={f.sha256}
                          preset={preset}
                          printerRef={CATALOG_ESTIMATE_PRINTER_REF}
                          enabled={canReadSelectedEstimate}
                          offerId={selectedOfferId}
                        />
                      </div>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {fmtSize(f.size_bytes)}
                    </span>
                    {isStl && stlFile !== undefined && (
                      <button
                        type="button"
                        aria-expanded={isExpanded}
                        aria-controls={`viewer-row-${f.id}`}
                        aria-label={`Toggle 3D preview for ${f.original_name}`}
                        onClick={() =>
                          setExpandedFileId(isExpanded ? null : f.id)
                        }
                        className="flex items-center gap-1 rounded px-2 py-1 text-xs text-foreground hover:bg-accent"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                        <Box className="h-3.5 w-3.5" />
                      </button>
                    )}
                    <a
                      href={`/api/models/${modelId}/files/${f.id}/content?download=1`}
                      className="flex items-center rounded px-2 py-1 text-xs text-foreground hover:bg-accent"
                      aria-label={t("catalog.actions.download")}
                    >
                      <Download className="size-3.5" aria-hidden />
                    </a>
                    {isAdmin && (
                      <button
                        type="button"
                        aria-label={t("catalog.actions.deleteFile", { name: f.original_name })}
                        disabled={deleteFile.isPending}
                        onClick={() => setPendingDelete({ id: f.id, name: f.original_name })}
                        className="flex items-center rounded px-2 py-1 text-xs text-destructive hover:bg-destructive/10 disabled:pointer-events-none disabled:opacity-50"
                      >
                        <Trash2 className="size-3.5" aria-hidden />
                      </button>
                    )}
                  </div>
                </div>
                {isExpanded && stlFile !== undefined && (
                  <div
                    id={`viewer-row-${f.id}`}
                    className="grid gap-3 border-t border-border bg-muted/10 p-3 lg:grid-cols-2"
                  >
                    <Suspense
                      fallback={<div className="text-xs">{t("viewer3d.loading_viewer")}</div>}
                    >
                      <Viewer3DInline
                        file={stlFile}
                        onExpand={() => {
                          setModalInitialId(f.id);
                          setModalOpen(true);
                        }}
                      />
                    </Suspense>
                    {/* EST-DISPLAY-1 (UX §C) — the full shipped EstimateDisplay beside the
                        viewer (stacks below on mobile), bound to the SAME global preset;
                        shares the chip's useEstimate query key ⇒ no second fetch. */}
                    <RowEstimatePanel
                      stlHash={f.sha256}
                      preset={preset}
                      printerRef={CATALOG_ESTIMATE_PRINTER_REF}
                      enabled={canReadSelectedEstimate}
                      offerId={selectedOfferId}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(next) => {
          if (!next) setPendingDelete(null);
        }}
        title={
          pendingDelete !== null
            ? t("catalog.actions.confirmDeleteFile", { name: pendingDelete.name })
            : ""
        }
        confirmLabel={t("catalog.actions.delete")}
        destructive
        pending={deleteFile.isPending}
        onConfirm={() => {
          if (pendingDelete === null) return;
          const deletedId = pendingDelete.id;
          deleteFile.mutate(deletedId, {
            onError: (err) => toast.error(err.message),
          });
          setExpandedFileId((current) => (current === deletedId ? null : current));
          if (modalInitialId === deletedId) {
            setModalOpen(false);
            setModalInitialId(undefined);
          }
          setPendingDelete(null);
        }}
      />
    </div>
  );
}
