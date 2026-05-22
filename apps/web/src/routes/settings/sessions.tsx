import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";
import { useId, useState } from "react";

import {
  useLogoutOthers,
  useRevokeSession,
  useSessions,
} from "@/modules/catalog/hooks/useSessions";
import { Button } from "@/ui/button";
import { ConfirmDialog } from "@/ui/custom/ConfirmDialog";
import { LoadingState } from "@/ui/custom/LoadingState";

const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;
const DEFAULT_PAGE_SIZE = 20;

/**
 * Story 12.5 — non-browser User-Agent patterns the filter hides by default.
 *
 * The check is client-side only: the backend returns every active session and
 * the page filters before render. This keeps the contract single-purpose
 * (server = data, client = presentation) and avoids leaking the "what counts
 * as a non-browser UA?" heuristic into a public API contract that downstream
 * consumers (audit dashboards, future mobile apps) might rely on.
 *
 * A UA is non-browser if it matches any of these prefixes/substrings OR if it
 * lacks the `Mozilla/` prefix entirely (every real-browser UA still carries
 * that legacy prefix for compat — its absence is a strong tell).
 */
const NON_BROWSER_UA_PATTERNS: readonly string[] = [
  "curl/",
  "httpie/",
  "python-requests/",
  "wget/",
  "Go-http-client/",
  "Java/",
  "okhttp/",
];

function isNonBrowserUserAgent(ua: string | null): boolean {
  if (!ua || ua.trim().length === 0) return true; // missing UA → treat as non-browser
  for (const pat of NON_BROWSER_UA_PATTERNS) {
    if (ua.includes(pat)) return true;
  }
  // Real browsers carry `Mozilla/` (even Chrome/Safari/Edge/Firefox). Anything
  // that doesn't is almost certainly a script or API client.
  return !ua.includes("Mozilla/");
}

interface SessionsSearch {
  page?: number;
  page_size?: number;
  /**
   * Story 12.5 — `show_api=1` reveals API / non-browser sessions in the list.
   * Default-absent keeps them hidden (FR7-SESSIONS-2 intent: the page is for
   * humans first, scripts second). Boolean-shaped via the literal `1` only,
   * mirroring `show_inactive=1` on /admin/users for URL-shape consistency.
   */
  show_api?: 1;
}

function Sessions() {
  const search = useSearch({ from: "/settings/sessions" });
  const navigate = useNavigate();
  const { t } = useTranslation();
  const pageSizeId = useId();
  const showApiId = useId();

  const page = search.page ?? 1;
  const pageSize = search.page_size ?? DEFAULT_PAGE_SIZE;
  const showApi = search.show_api === 1;

  // Backend default sort = last_used_at DESC, current-session pinned to row 0.
  // No need to pass sort params unless we ever expose a user-facing sort UI.
  const { data, isLoading } = useSessions({ page, page_size: pageSize });
  const revoke = useRevokeSession();
  const logoutOthers = useLogoutOthers();
  const [pendingCurrentRevoke, setPendingCurrentRevoke] = useState<string | null>(null);

  function updateSearchParams(
    next: Partial<{
      page: number;
      page_size: number;
      show_api: 1 | undefined;
    }>,
  ) {
    void navigate({
      to: "/settings/sessions",
      search: (prev) => {
        const merged: Record<string, unknown> = { ...prev, ...next };
        for (const key of Object.keys(merged)) {
          if (merged[key] === undefined || merged[key] === "") {
            delete merged[key];
          }
        }
        return merged;
      },
      replace: true,
    });
  }

  if (isLoading) return <LoadingState variant="spinner" className="p-6" />;

  const rawItems = data?.items ?? [];
  const total = data?.total ?? rawItems.length;

  // Client-side UA filter. The backend page window is sized by `pageSize`, so
  // hiding non-browser entries can shrink the visible row count below
  // `pageSize` — that's a deliberate trade-off (simpler than asking the
  // backend to participate in the heuristic). The page indicator below
  // reflects the backend's total, which always counts every session.
  const items = showApi
    ? rawItems
    : rawItems.filter((s) => !isNonBrowserUserAgent(s.user_agent));

  // Codex P2 (12.5 review): derive "logout all others" availability from the
  // UNFILTERED response — the UA-filter is a view preference, not an action
  // boundary. If the user has API sessions that are hidden by the default
  // filter, the global revoke still applies to them and the button must stay
  // enabled. (Empty-state — no other sessions at all — falls out of total > 1.)
  const hasOthers = total > 1;
  // Codex P3 (12.5 review): clamp the visible page label when a mutation
  // (e.g. "log out everywhere") shrinks `total` below the current offset,
  // otherwise the indicator renders ranges like "Showing 21–1 of 1". The
  // effective page is the smaller of the requested page and the last page
  // that actually has rows.
  const lastPage = total === 0 ? 1 : Math.max(1, Math.ceil(total / pageSize));
  const visiblePage = Math.min(page, lastPage);
  const first = total === 0 ? 0 : (visiblePage - 1) * pageSize + 1;
  const last = Math.min(visiblePage * pageSize, total);

  async function onRevoke(familyId: string, isCurrent: boolean) {
    if (isCurrent) {
      // Defer to the ConfirmDialog and let it call performCurrentRevoke().
      setPendingCurrentRevoke(familyId);
      return;
    }
    await revoke.mutateAsync(familyId);
  }

  async function performCurrentRevoke() {
    if (pendingCurrentRevoke === null) return;
    const familyId = pendingCurrentRevoke;
    setPendingCurrentRevoke(null);
    await revoke.mutateAsync(familyId);
    await navigate({ to: "/login", replace: true });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">{t("auth.sessions.title")}</h1>
      <p className="text-sm text-muted-foreground">
        {t("auth.sessions.description")}
      </p>

      <div className="flex flex-wrap items-end gap-3">
        <Button
          variant="secondary"
          disabled={!hasOthers || logoutOthers.isPending}
          onClick={() => logoutOthers.mutate()}
        >
          {t("auth.sessions.logout_others")}
        </Button>

        <div className="grid gap-1.5">
          <label htmlFor={pageSizeId} className="text-sm font-medium">
            {t("auth.sessions.page_size_label")}
          </label>
          <select
            id={pageSizeId}
            value={pageSize}
            className="rounded border border-border bg-background px-3 py-1.5 text-sm"
            onChange={(e) =>
              updateSearchParams({
                page_size: Number(e.target.value),
                page: 1,
              })
            }
          >
            {PAGE_SIZE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        {/* Story 12.5 — default-hide API/non-browser sessions; checkbox reveals them. */}
        <div className="flex items-center gap-2 self-end py-1.5">
          <input
            id={showApiId}
            type="checkbox"
            checked={showApi}
            aria-label={t("auth.sessions.filter_show_api")}
            className="size-4 rounded border-border"
            onChange={(e) =>
              updateSearchParams({
                show_api: e.target.checked ? 1 : undefined,
                page: 1,
              })
            }
          />
          <label htmlFor={showApiId} className="text-sm font-medium">
            {t("auth.sessions.filter_show_api")}
          </label>
        </div>
      </div>

      {/* Desktop: table */}
      <div className="hidden rounded border border-border sm:block">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">
                {t("auth.sessions.device")}
              </th>
              <th className="px-3 py-2 text-left">{t("auth.sessions.ip")}</th>
              <th className="px-3 py-2 text-left">
                {t("auth.sessions.last_used")}
              </th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-6 text-center text-muted-foreground"
                >
                  {t("auth.sessions.empty")}
                </td>
              </tr>
            ) : (
              items.map((s) => {
                const isApi = isNonBrowserUserAgent(s.user_agent);
                const rowClassName = isApi
                  ? "border-t border-border bg-muted/30 text-muted-foreground"
                  : "border-t border-border";
                return (
                  <tr key={s.family_id} className={rowClassName}>
                    <td className="px-3 py-2">
                      {s.user_agent || t("auth.sessions.unknown_device")}
                      {s.is_current && (
                        <span className="ml-2 rounded bg-primary/15 px-1.5 py-0.5 text-xs">
                          {t("auth.sessions.current")}
                        </span>
                      )}
                      {isApi && (
                        <span className="ml-2 rounded border border-border px-1.5 py-0.5 text-xs">
                          {t("auth.sessions.api_badge")}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {s.ip || t("auth.sessions.unknown_ip")}
                    </td>
                    <td className="px-3 py-2" title={s.last_used_at ?? ""}>
                      {s.last_used_at
                        ? new Date(s.last_used_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => void onRevoke(s.family_id, s.is_current)}
                      >
                        {t("auth.sessions.revoke")}
                      </Button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile: cards */}
      <div className="space-y-2 sm:hidden">
        {items.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground">
            {t("auth.sessions.empty")}
          </p>
        ) : (
          items.map((s) => {
            const isApi = isNonBrowserUserAgent(s.user_agent);
            const cardClassName = isApi
              ? "rounded border border-border bg-muted/30 p-3 text-sm text-muted-foreground"
              : "rounded border border-border p-3 text-sm";
            return (
              <div key={s.family_id} className={cardClassName}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {s.user_agent || t("auth.sessions.unknown_device")}
                  </span>
                  <div className="flex shrink-0 gap-1">
                    {s.is_current && (
                      <span className="rounded bg-primary/15 px-1.5 py-0.5 text-xs">
                        {t("auth.sessions.current")}
                      </span>
                    )}
                    {isApi && (
                      <span className="rounded border border-border px-1.5 py-0.5 text-xs">
                        {t("auth.sessions.api_badge")}
                      </span>
                    )}
                  </div>
                </div>
                <div className="mt-1 text-muted-foreground">
                  {s.ip || t("auth.sessions.unknown_ip")} &middot;{" "}
                  {s.last_used_at
                    ? new Date(s.last_used_at).toLocaleString()
                    : "—"}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => void onRevoke(s.family_id, s.is_current)}
                >
                  {t("auth.sessions.revoke")}
                </Button>
              </div>
            );
          })
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {t("auth.sessions.pagination_label", { first, last, total })}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            onClick={() => updateSearchParams({ page: page - 1 })}
          >
            {t("auth.sessions.pagination_previous")}
          </button>
          <button
            type="button"
            disabled={page * pageSize >= total}
            className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-50"
            onClick={() => updateSearchParams({ page: page + 1 })}
          >
            {t("auth.sessions.pagination_next")}
          </button>
        </div>
      </footer>

      <ConfirmDialog
        open={pendingCurrentRevoke !== null}
        onOpenChange={(next) => {
          if (!next) setPendingCurrentRevoke(null);
        }}
        title={t("auth.sessions.confirm_revoke_current")}
        confirmLabel={t("auth.sessions.revoke")}
        destructive
        pending={revoke.isPending}
        onConfirm={() => void performCurrentRevoke()}
      />
    </div>
  );
}

export const Route = createFileRoute("/settings/sessions")({
  // Initiative 6 Story 11.3 — shell-level AuthGate (AppShell.tsx Decision O)
  // handles the anonymous redirect; per-route wrapper removed.
  component: Sessions,
  validateSearch: (raw: Record<string, unknown>): SessionsSearch => {
    const out: SessionsSearch = {};
    if (typeof raw.page === "number" && raw.page >= 1) out.page = raw.page;
    else if (typeof raw.page === "string" && /^\d+$/.test(raw.page))
      out.page = Number(raw.page);
    if (typeof raw.page_size === "number") {
      if ((PAGE_SIZE_OPTIONS as readonly number[]).includes(raw.page_size))
        out.page_size = raw.page_size;
    } else if (typeof raw.page_size === "string" && /^\d+$/.test(raw.page_size)) {
      const n = Number(raw.page_size);
      if ((PAGE_SIZE_OPTIONS as readonly number[]).includes(n)) out.page_size = n;
    }
    // Story 12.5 — accept only the literal `1` (number or string); any other
    // value is treated as absent so the page falls back to the safe default
    // (hide non-browser sessions).
    if (raw.show_api === 1 || raw.show_api === "1") {
      out.show_api = 1;
    }
    return out;
  },
});
