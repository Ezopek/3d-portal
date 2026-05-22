import { Navigate, createFileRoute } from "@tanstack/react-router";

import type { InviteStatus } from "@/lib/api-types";
import { InvitesPage } from "@/modules/admin/InvitesPage";
import { useAuth } from "@/shell/AuthContext";

interface AdminInvitesSearch {
  page?: number;
  page_size?: number;
  status?: InviteStatus;
}

function AdminInvitesRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  if (isLoading) return null;
  // Defer to AppShell.AuthGate for anonymous users so the original pathname
  // is preserved in the /login?next= param (Decision O contract).
  if (!isAuthenticated) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <InvitesPage />;
}

const STATUS_VALUES: InviteStatus[] = ["active", "used", "expired", "revoked"];

export const Route = createFileRoute("/admin/invites")({
  // Initiative 6 Story 11.3 — shell-level AuthGate (AppShell.tsx Decision O)
  // handles the authenticated-vs-anonymous redirect. AdminInvitesRoute's
  // inner `isAdmin` check remains as the role-tier gate.
  component: AdminInvitesRoute,
  validateSearch: (raw: Record<string, unknown>): AdminInvitesSearch => {
    const out: AdminInvitesSearch = {};
    if (typeof raw.page === "number" && raw.page >= 1) out.page = raw.page;
    else if (typeof raw.page === "string" && /^\d+$/.test(raw.page))
      out.page = Number(raw.page);
    if (typeof raw.page_size === "number") out.page_size = raw.page_size;
    else if (typeof raw.page_size === "string" && /^\d+$/.test(raw.page_size))
      out.page_size = Number(raw.page_size);
    if (
      typeof raw.status === "string" &&
      (STATUS_VALUES as readonly string[]).includes(raw.status)
    ) {
      out.status = raw.status as InviteStatus;
    }
    return out;
  },
});
