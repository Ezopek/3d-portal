import { Navigate, createFileRoute } from "@tanstack/react-router";

import { ProfileLibraryPage } from "@/modules/admin/ProfileLibraryPage";
import { useAuth } from "@/shell/AuthContext";

function AdminProfileLibraryRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  if (isLoading) return null;
  // Defer to AppShell.AuthGate for anonymous users so the original pathname is preserved in
  // the /login?next= param (Decision O contract). The inner Navigate to / is the role-tier
  // gate for member-authenticated users who lack the admin role (Init 10 retro rule).
  if (!isAuthenticated) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <ProfileLibraryPage />;
}

export const Route = createFileRoute("/admin/profile-library")({
  component: AdminProfileLibraryRoute,
});
