/**
 * TypeScript counterparts of the API response schemas.
 *
 * Source of truth: apps/api/app/modules/sot/schemas.py and
 * apps/api/app/modules/auth/models.py. Keep this file in sync by hand
 * when the Pydantic schemas change. UUIDs and datetimes are strings on
 * the wire (canonical UUID string, ISO 8601 timestamp).
 */

export type Role = "admin" | "agent" | "member";

export interface MeResponse {
  id: string;
  email: string;
  display_name: string;
  role: Role;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  partial_auth: false; // discriminator — always false on this shape
  user: MeResponse;
  totp_enroll_required: boolean; // Story 7.4 — true when Decision F enforcement requires enrollment
}

export interface PartialAuthResponse {
  partial_auth: true;
  totp_required: true;
  partial_token: string;
}

export interface VerifyRequest {
  partial_token: string;
  code: string; // ^(\d{6}|[0-9a-f]{8})$
}

// --- Categories ---

export interface CategorySummary {
  id: string;
  parent_id: string | null;
  slug: string;
  name_en: string;
  name_pl: string | null;
}

export interface CategoryNode extends CategorySummary {
  children: CategoryNode[];
  /** Total non-deleted models in this subtree (self + all descendants). */
  model_count: number;
}

export interface CategoryTree {
  roots: CategoryNode[];
}

// --- Tags ---

export interface TagRead {
  id: string;
  slug: string;
  name_en: string;
  name_pl: string | null;
}

// --- Files ---

export type ModelFileKind =
  | "stl"
  | "image"
  | "print"
  | "source"
  | "archive_3mf"
  | "stl_preview";

export interface ModelFileRead {
  id: string;
  model_id: string;
  kind: ModelFileKind;
  original_name: string;
  storage_path: string;
  sha256: string;
  size_bytes: number;
  mime_type: string;
  position: number | null;
  selected_for_render: boolean;
  created_at: string;
}

export interface FileListResponse {
  items: ModelFileRead[];
}

// --- External links / notes / prints ---

export type ExternalSource =
  | "printables"
  | "thangs"
  | "makerworld"
  | "cults3d"
  | "thingiverse"
  | "crealitycloud"
  | "other";

export interface ExternalLinkRead {
  id: string;
  model_id: string;
  source: ExternalSource;
  external_id: string | null;
  url: string;
  created_at: string;
  updated_at: string;
}

export type NoteKind = "description" | "operational" | "ai_review" | "other";

export interface NoteRead {
  id: string;
  model_id: string;
  kind: NoteKind;
  body: string;
  // Initiative 10 Story 16.1 (Decision L) — bilingual fields for description-kind
  // notes. Null on non-description notes and on legacy description rows; frontend
  // falls back to `body` when both are null.
  body_pl: string | null;
  body_en: string | null;
  author_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrintRead {
  id: string;
  model_id: string;
  photo_file_id: string | null;
  printed_at: string | null; // YYYY-MM-DD
  note: string | null;
  created_at: string;
  updated_at: string;
}

// --- Models ---

export type ModelSource =
  | "unknown"
  | "printables"
  | "thangs"
  | "makerworld"
  | "cults3d"
  | "thingiverse"
  | "crealitycloud"
  | "own"
  | "other";

export type ModelStatus = "not_printed" | "printed" | "in_progress" | "broken";

export interface ModelSummary {
  id: string;
  slug: string;
  name_en: string;
  name_pl: string | null;
  category_id: string;
  source: ModelSource;
  status: ModelStatus;
  rating: number | null;
  thumbnail_file_id: string | null;
  date_added: string; // YYYY-MM-DD
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  tags: TagRead[];
  /** Top up to 4 image/print file IDs, ordered by (position NULLS LAST, created_at). */
  gallery_file_ids: string[];
  /** Total image+print files for this model. */
  image_count: number;
}

export interface ModelDetail extends ModelSummary {
  category: CategorySummary;
  files: ModelFileRead[];
  prints: PrintRead[];
  notes: NoteRead[];
  external_links: ExternalLinkRead[];
}

export interface ModelListResponse {
  items: ModelSummary[];
  total: number;
  offset: number;
  limit: number;
}

// --- Sessions ---

export interface Session {
  family_id: string;
  last_used_at: string | null;
  family_issued_at: string;
  ip: string | null;
  user_agent: string | null;
  is_current: boolean;
}

/** Story 12.5 — sort columns accepted by `GET /api/auth/sessions`. */
export type SessionsSortBy = "last_used_at" | "created_at";
export type SessionsSortOrder = "asc" | "desc";

export interface SessionsResponse {
  items: Session[];
  /** Story 12.5: total unpaginated count so the UI can render N-M of T. */
  total: number;
  page: number;
  page_size: number;
}

export interface SessionsListParams {
  page?: number;
  page_size?: number;
  sort_by?: SessionsSortBy;
  sort_order?: SessionsSortOrder;
}

// --- Admin users (Story 8.2) ---

export type AdminUserSortBy =
  | "email"
  | "role"
  | "created_at"
  | "last_active_at";
export type AdminUserSortOrder = "asc" | "desc";

export interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  created_at: string;
  last_active_at: string | null;
  totp_enabled: boolean;
  is_active: boolean;
  force_2fa_enrollment: boolean;
}

export interface AdminUsersListResponse {
  total: number;
  items: AdminUser[];
  page: number;
  page_size: number;
}

// --- Admin users mutations (Story 8.3) ---

export interface UserMutationRequest {
  role?: Role;
  is_active?: boolean;
}

// --- Admin 2FA overrides (Story 8.4) ---
// The two new POST endpoints take no request body, so no
// request/response interfaces are needed — see
// `useForce2faEnrollmentAdminUser` / `useForceDisable2faAdminUser`
// in `modules/admin/hooks/useAdminUsers.ts`.

// --- Password reset (Story 8.5) ---

export interface PasswordResetMintResponse {
  reset_url: string;
  expires_at: string;
}

// --- TOTP 2FA (Story 7.2) ---

export interface TotpEnrollResponse {
  qr_svg: string;
  manual_secret: string;
  enrollment_token: string;
}

export interface TotpConfirmRequest {
  enrollment_token: string;
  code: string;
}

export interface TotpConfirmResponse {
  recovery_codes: string[];
  batch_id: string;
  generated_at: string;
}

export interface TotpStatusResponse {
  enabled: boolean;
  batch_id: string | null;
  generated_at: string | null;
  codes_remaining: number | null;
}

// --- TOTP 2FA re-auth (Story 7.5) ---

export interface ReauthRequest {
  password: string;
  totp_code: string;
}

export type RegenerateResponse = TotpConfirmResponse;

// --- Story 8.6: Admin invites tab ---

export type InviteRoleRequest = "member" | "admin";
export type InviteTTLPreset =
  | "ONE_DAY"
  | "THREE_DAYS"
  | "SEVEN_DAYS"
  | "THIRTY_DAYS";
export type InviteStatus = "active" | "used" | "revoked" | "expired";

export interface AdminInviteRow {
  id: string;
  invite_id: string;
  token_hash: string;
  role: InviteRoleRequest;
  generated_by_user_id: string | null;
  generated_at: string;
  ttl_seconds: number;
  expires_at: string;
  used_by_user_id: string | null;
  used_at: string | null;
  used_from_ip: string | null;
  revoked_at: string | null;
  status: InviteStatus;
}

export interface AdminInvitesListResponse {
  items: AdminInviteRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface GenerateInviteRequest {
  role: InviteRoleRequest;
  ttl_preset?: InviteTTLPreset;
  ttl_seconds?: number;
}

export interface GenerateInviteResponse {
  invite_id: string;
  token: string;
  role: InviteRoleRequest;
  generated_at: string;
  ttl_seconds: number;
  expires_at: string;
  registration_url: string;
}

// --- Audit log ---

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  at: string;
}

export interface AuditLogResponse {
  items: AuditLogEntry[];
}

// --- Initiative 19 Story 31.2 (Decision AF) — Spoolman read-only DTOs ---

export interface VendorView {
  id: number;
  name: string;
}

export interface FilamentView {
  id: number;
  name: string;
  vendor_id: number | null;
  vendor_name: string | null;
  material: string | null;
  color_hex: string | null;
  price: number | null;
  weight: number | null;
  spool_weight: number | null;
}

export interface SpoolView {
  id: number;
  filament_id: number;
  price: number | null;
  remaining_weight: number | null;
  initial_weight: number | null;
  used_weight: number | null;
  spool_weight: number | null;
  first_used: string | null;
  last_used: string | null;
  archived: boolean;
  lot_nr: string | null;
}

export interface SpoolsSummaryResponse {
  spools: SpoolView[];
  filaments: FilamentView[];
  vendors: VendorView[];
  fetched_at: string | null;
  last_success_ts: string | null;
}

// --- Initiative 20 Story 32.6 — UI-safe estimate read DTOs (slicer/schemas.py) ---
// These mirror the backend `EstimateView` projection. They carry ONLY UI fields —
// NO settings_ids / bundle_hash / stl_hash / Orca key / g-code (FR20-PRESET-1).

// The material classes the resolver supports (FR20). Material names are UNtranslated
// (a portal↔Orca naming convention, NFR20-I18N-PARITY-1), so they are a literal union.
export type MaterialClass = "PLA" | "PETG" | "PCTG" | "TPU";

// The portal-defined quality tiers the resolver maps to Orca process profiles.
export type QualityTier = "aesthetic" | "standard" | "strong";

// The estimate lifecycle the UI renders: the Decision AJ EstimateStatus
// {fresh,stale,queued,failed} plus "absent" (a 200 store miss). "loading" is a
// query/transport state the FE owns; it is never a server-reported value.
export type UIEstimateStatus =
  | "fresh"
  | "stale"
  | "queued"
  | "failed"
  | "absent"
  | "not_computed";

// The granular parse-failure reasons the backend classifies (rendered "here's why").
export type EstimateFailureReason =
  | "parse_failure"
  | "missing_metadata_line"
  | "unparseable_time"
  | "unparseable_numeric";

export interface EstimateWarningView {
  code: string;
  message: string;
}

export interface OverrideContextView {
  material_class: MaterialClass;
  quality_tier: QualityTier;
  pinned_filament_name: string | null;
  custom_overrides_applied: boolean;
  purchase_url: string | null;
}

// Story 35.5 — mirrors slicer/schemas.py ProfileSelectionContextView.
// orca_filament_profile_name is admin-scoped — never render in user-facing UI.
export type EstimateProfileSource =
  | "exact_filament_mapping"
  | "default_material_profile"
  | "unavailable_no_profile";

export interface ProfileSelectionContextView {
  estimate_profile_source: EstimateProfileSource;
  selected_material: string | null;
  selected_spoolman_filament_ref: string | null;
  selected_filament_name: string | null;
  orca_filament_profile_name: string | null;
}

export interface EstimateView {
  status: UIEstimateStatus;
  time_seconds: number | null;
  filament_g: number | null;
  filament_mm: number | null;
  filament_cm3: number | null;
  filament_cost: number | null;
  currency: string | null;
  computed_at: string | null;
  warnings: EstimateWarningView[];
  failure_reason: EstimateFailureReason | null;
  override_context: OverrideContextView;
  profile_selection_context?: ProfileSelectionContextView | null;
  offer_id?: string | null;
}

// EST-RECOMPUTE-1 — the guarded POST /api/estimates/recompute response. `enqueued` is the
// FACT that a re-slice was queued ON THIS CALL (false only when a recompute was already in
// flight, the self-DoS guard); `estimate` is the honest projected state (the same
// `EstimateView` the read endpoint returns — no bundle_hash / job_id / queue internals).
export interface RecomputeResponse {
  enqueued: boolean;
  estimate: EstimateView;
}

// --- Story 33.1 (Decision AK) — read-only admin profile inventory DTOs ---
// Mirror `slicer/schemas.py` AdminProfile*. Carry ONLY the projected fields — NO Orca
// keys / paths / g-code (the AC-9 no-leak fence, mirrored on the FE).

// The single primary status per slot, by the AC-4 precedence
// (incompatible → not_imported → not_resolvable → offerable).
export type AdminProfileStatus =
  | "offerable"
  | "not_imported"
  | "not_resolvable"
  | "incompatible";

export interface AdminProfileProvenance {
  // The vendored system-tree content hash (the FE may truncate it for display); null on a
  // slot that does not resolve.
  source_system_tree_hash: string | null;
  orca_version: string | null;
}

export interface AdminProfileSlot {
  material_class: MaterialClass;
  quality_tier: QualityTier;
  imported: boolean;
  resolvable: boolean;
  compatible: boolean;
  // offerable === (imported && resolvable && compatible)
  offerable: boolean;
  status: AdminProfileStatus;
  // Structured reason category (the FE localizes it); null only when offerable.
  reason: string | null;
  // Operator-assigned label — reserved for the Story 33.3 label store, null in 33.1.
  portal_label: string | null;
  provenance: AdminProfileProvenance;
}

export interface AdminProfileInventoryResponse {
  printer_ref: string;
  slots: AdminProfileSlot[];
}

// --- Story 33.2 (Decision AL) — validated import/publish write path ---
// The structured rejection detail an import returns (413/422 `detail`). `reason_category`
// is the machine-readable category the FE localizes (admin fails closed/visible).
export interface ProfileImportRejection {
  reason_category: string;
  message: string;
}

// --- PROFILE-LIB-1 (Decision AM) — separate-block profile library ---
// Mirror `slicer/schemas.py` ProfileLibraryBlock. Curated metadata ONLY — NO raw Orca key
// body / path / g-code (the AC-13 leak fence, mirrored on the FE). Coexists with the grid
// (33.1/33.2) DTOs above and never replaces them.

export type ProfileType = "machine" | "process" | "filament";

export type ProfileValidationState = "usable" | "requires_attention" | "error";

export interface StaleProfileOfferRef {
  offer_id: string;
  label: string;
  publish_state: OfferPublishState;
}

export interface ProfileLibraryBlock {
  block_id: string;
  profile_type: ProfileType;
  name: string;
  source: string | null;
  is_system: boolean;
  inherit: string | null;
  inherit_chain: string[];
  settings_id: string | null;
  // Normalized generic material category (PLA/PETG/PCTG/TPU), null when absent/out-of-table.
  material_type: string | null;
  compatible_printers: string[];
  validation_state: ProfileValidationState;
  // Machine-readable reason categories (the FE localizes them); empty when usable.
  reasons: string[];
  portal_label: string | null;
  imported_at: string;
  imported_by: string;
  // Added 38.1: populated by import/upsert only; empty for normal list callers.
  stale_offers: StaleProfileOfferRef[];
}

export interface ProfileLibraryListResponse {
  blocks: ProfileLibraryBlock[];
}

// --- PROFILE-OFFER-1 (Decision AN) — PrintProfileOffer / ProfileChain ---
// Mirror `slicer/schemas.py` PrintProfileOffer*. Curated offer config + embedded chain refs
// + read-time validation + a leak-fenced `chain_blocks` echo of the referenced blocks — NO
// raw Orca key body / path / g-code (the AC-8 leak fence, mirrored on the FE). Coexists with
// the grid (33.1/33.2) and library (PROFILE-LIB-1) DTOs above and never replaces them.

export type OfferVisibility = "hidden" | "visible";
export type OfferPublishState = "published" | "unpublished";
export type OfferSyncState = "current" | "stale" | "unknown";

// The per-offer validation state (AC-4): a stored offer is at worst `invalid` (a referenced
// block went missing / wrong-typed); `requires_attention` is stored + listed + flagged.
export type OfferValidationState = "usable" | "requires_attention" | "invalid";

export interface ProfileChainRef {
  machine_block_id: string;
  process_block_id: string;
  filament_block_id: string;
}

export interface PrintProfileOffer {
  offer_id: string;
  // `label` / block names / material types render as DATA (untranslated).
  label: string;
  description: string | null;
  chain: ProfileChainRef;
  visibility: OfferVisibility;
  is_default: boolean;
  // Constrained to the generic set {PLA,PETG,PCTG,TPU} (server-validated; out-of-table ⇒ 422).
  compatible_material_categories: string[];
  // RECOMPUTED at read time against the current library (a stale `usable` is never served).
  validation_state: OfferValidationState;
  // Machine-readable reason categories (the FE localizes them); empty when usable.
  reasons: string[];
  // Curated metadata of the referenced blocks (no raw Orca body); a missing block is omitted.
  chain_blocks: ProfileLibraryBlock[];
  created_at: string;
  created_by: string;
  updated_at: string;
  publish_state: OfferPublishState;
  published_bundle_hash: string | null;
  published_at: string | null;
  published_by: string | null;
  source_snapshot_ref: string | null;
  published_stl_hash: string | null;
  sync_state: OfferSyncState;
}

export interface PrintProfileOfferListResponse {
  offers: PrintProfileOffer[];
}

// The create body — `visibility` defaults `hidden` and `is_default` `false` server-side.
export interface PrintProfileOfferCreate {
  label: string;
  description?: string | null;
  chain: ProfileChainRef;
  visibility?: OfferVisibility;
  is_default?: boolean;
  compatible_material_categories?: string[];
}

// The patch body — label/visibility/default/categories ONLY; the chain is immutable on PATCH.
export interface PrintProfileOfferUpdate {
  label?: string;
  description?: string | null;
  visibility?: OfferVisibility;
  is_default?: boolean;
  compatible_material_categories?: string[];
}

// Optional server-side filters for the offer list (AC-10). `material_category` reuses the
// generic material table (= MaterialClass); both narrow the listing, not the validation.
export interface ProfileOffersFilters {
  material_category?: MaterialClass;
  visibility?: OfferVisibility;
}

export interface OfferPublishResult {
  offer_id: string;
  published_bundle_hash: string;
  publish_state: OfferPublishState;
  published_at: string;
  estimate_job_id: string;
  estimate: unknown | null;
}

export interface OfferEstimateRecomputeResponse {
  dry_run: boolean;
  inspected: number;
  cells_total: number;
  cells_resolved: number;
  cells_resolve_failed: number;
  enqueued: number;
  already_fresh: number;
  missing_stl: number;
  errors: number;
  would_enqueue: number;
}

export interface OfferEstimateRecomputeRequest {
  dry_run?: boolean;
  visible_only?: boolean;
  offer_id?: string | null;
  max_cells?: number | null;
}

// --- Story 36.1 — member-facing published offer DTOs ---
// Mirrors slicer/schemas.py MemberPublishedOfferView.
// NFR24-LEAKFENCE-1: bundle_hash / raw chain block IDs / sidecar paths ABSENT.
export interface MemberPublishedOfferView {
  offer_id: string;
  portal_label: string; // admin-assigned display name; DATA (untranslated)
  quality_tier: string | null; // "aesthetic"|"standard"|"strong"; null if block unavailable
  compatible_material_categories: string[];
  printer_name: string | null; // null if machine block unavailable
  is_default: boolean;
}

export interface MemberPublishedOfferListResponse {
  offers: MemberPublishedOfferView[];
}
