// Initiative 10 Story 16.4 — admin manual model add UI (Decision N).
//
// Initiative 13 Story 20.2 refactor: form extracted into reusable
// AddModelForm component so /catalog AddModelButton (toolbar) and this
// dedicated route both consume the same form shape. Route remains as a
// discoverable URL for operators who prefer direct navigation.

import { Navigate, createFileRoute, useNavigate } from "@tanstack/react-router";

import { AddModelForm } from "@/modules/admin/AddModelForm";
import { useAuth } from "@/shell/AuthContext";

function AdminModelNewRoute() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();
  const navigate = useNavigate();

  if (isLoading) return null;
  if (!isAuthenticated) return null; // AuthGate handles via shell
  if (!isAdmin) return <Navigate to="/catalog" replace />;

  return (
    <AddModelForm
      onSuccess={(model) =>
        void navigate({ to: "/catalog/$id", params: { id: model.id } })
      }
      onCancel={() => void navigate({ to: "/catalog" })}
    />
  );
}

export const Route = createFileRoute("/admin/models/new")({
  component: AdminModelNewRoute,
});
