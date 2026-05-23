// Initiative 10 Story 16.3 — share-link API helpers.
//
// Two surface families:
//
// - **Authenticated member-side** (`/api/admin/share` POST,
//   `/api/me/share-links` GET/DELETE) — routed through the standard `api()`
//   client to inherit CSRF header + 401-retry path.
// - **Anonymous viewer-side** (`/api/share/<token>` GET, `/api/share/<token>/files/...`)
//   — MUST NOT carry cookies (NFR10-SHARE-SECURITY-1). Uses bare `fetch()`
//   with `credentials: "omit"` and NO CSRF header so the request hits the
//   server as a pure anonymous client.

import { api } from "@/lib/api";

export interface CreateShareResponse {
  token: string;
  url: string;
  expires_at: string;
}

export interface ShareToken {
  token: string;
  model_id: string;
  expires_at: string;
  created_by: string;
  created_at: string;
}

export interface ShareModelView {
  id: string;
  name_en: string;
  name_pl: string | null;
  category: string;
  tags: string[];
  thumbnail_url: string | null;
  has_3d: boolean;
  images: string[];
  notes_en: string;
  notes_pl: string;
  stl_url: string | null;
  /**
   * Initiative 12 Story 19.7 round-2 (Codex P2 fix) — size in bytes of the
   * STL surfaced via stl_url, used client-side by the embedded
   * Viewer3DInline to gate the large-STL confirm dialog (>50 MB triggers
   * the gate per perf module). null when no STL exists or when the backend
   * can't determine the size — the gate then skips.
   */
  stl_size_bytes: number | null;
}

export type ShareTtlPreset = 1 | 3 | 7;

/** Create a share link. Authenticated (member or admin). */
export async function createShareLink(
  modelId: string,
  ttlDays: ShareTtlPreset,
): Promise<CreateShareResponse> {
  // `api()` prepends the `/api` base — pass the path WITHOUT the prefix to
  // avoid `/api/api/...` double-prefix (Codex P1 2026-05-22).
  return api<CreateShareResponse>("/admin/share", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId, expires_in_hours: ttlDays * 24 }),
  });
}

/** List the current user's active share tokens. Authenticated. */
export async function listMyShareLinks(): Promise<ShareToken[]> {
  const r = await api<{ tokens: ShareToken[] }>("/me/share-links");
  return r.tokens;
}

/** Revoke one of the current user's share tokens. Authenticated. */
export async function revokeMyShareLink(token: string): Promise<void> {
  await api<void>(`/me/share-links/${token}`, { method: "DELETE" });
}

/**
 * Fetch the anonymous share-view payload. Used by the /share/$token route.
 *
 * MUST NOT carry cookies — anonymous viewer is fully detached from the
 * authenticated user (NFR10-SHARE-SECURITY-1). Bare fetch with
 * `credentials: "omit"` to defend against accidental cookie leak even if
 * the user is logged in in the same browser.
 */
export async function fetchShareView(token: string): Promise<ShareModelView> {
  const r = await fetch(`/api/share/${encodeURIComponent(token)}`, {
    credentials: "omit",
    headers: { Accept: "application/json" },
  });
  if (!r.ok) {
    throw new Error(`share_view_${r.status}`);
  }
  return (await r.json()) as ShareModelView;
}
