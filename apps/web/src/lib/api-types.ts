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
  access_token: string;
  token_type: "bearer";
  expires_in: number;
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

export type ModelFileKind = "stl" | "image" | "print" | "source" | "archive_3mf";

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
  author_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrintRead {
  id: string;
  model_id: string;
  photo_file_id: string | null;
  printed_at: string | null;  // YYYY-MM-DD
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
  | "own"
  | "other";

export type ModelStatus = "not_printed" | "printed" | "in_progress" | "broken";

export interface ModelSummary {
  id: string;
  legacy_id: string | null;
  slug: string;
  name_en: string;
  name_pl: string | null;
  category_id: string;
  source: ModelSource;
  status: ModelStatus;
  rating: number | null;
  thumbnail_file_id: string | null;
  date_added: string;  // YYYY-MM-DD
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  tags: TagRead[];
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
