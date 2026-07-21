import { Navigate, createFileRoute } from "@tanstack/react-router";

import { TagGroupsPage } from "@/modules/admin/TagGroupsPage";
import { useAuth } from "@/shell/AuthContext";

function AdminTagGroupsRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  if (isLoading) return null;
  // Defer to AppShell.AuthGate for anonymous users so the original pathname is preserved in
  // the /login?next= param (Decision O contract). The inner Navigate to / is the role-tier
  // gate for member-authenticated users who lack the admin role (Init 10 retro rule).
  if (!isAuthenticated) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <TagGroupsPage />;
}

export const Route = createFileRoute("/admin/tag-groups")({
  component: AdminTagGroupsRoute,
});
