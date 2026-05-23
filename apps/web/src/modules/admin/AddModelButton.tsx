// Initiative 13 Story 20.2 — admin-only "Add Model" CTA in the catalog
// toolbar. Operator-aligned 2026-05-23: top-right placement next to filter
// controls; modal-over-route shape; full form (not quick-add) — see
// sprint-change-proposal-2026-05-23-init-11-15.md § Initiative 13 Story 20.2.

import { useNavigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/shell/AuthContext";
import { Button } from "@/ui/button";

import { AddModelModal } from "./AddModelModal";

export function AddModelButton() {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  // Role gate at render time — non-admin users never see the button.
  // The backend POST /api/admin/models is also auth-gated; FE gate is
  // strictly UX (no admin-only error toast for member users).
  if (!isAdmin) return null;

  return (
    <>
      <Button
        type="button"
        size="sm"
        variant="default"
        onClick={() => setOpen(true)}
      >
        <Plus className="size-4" aria-hidden />
        {t("admin.models.new.toolbar_cta")}
      </Button>
      <AddModelModal
        open={open}
        onOpenChange={setOpen}
        onCreated={(model) => {
          void navigate({ to: "/catalog/$id", params: { id: model.id } });
        }}
      />
    </>
  );
}
