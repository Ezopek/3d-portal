import { Navigate, createFileRoute } from "@tanstack/react-router";

import { ProfilesPage } from "@/modules/admin/ProfilesPage";
import { useAuth } from "@/shell/AuthContext";

function AdminProfilesRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  if (isLoading) return null;
  // Defer to AppShell.AuthGate for anonymous users so the original pathname is preserved in
  // the /login?next= param (Decision O contract). The inner Navigate to / is the role-tier
  // gate for member-authenticated users who lack the admin role (Init 10 retro rule).
  if (!isAuthenticated) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <ProfilesPage />;
}

export const Route = createFileRoute("/admin/profiles")({
  component: AdminProfilesRoute,
});
