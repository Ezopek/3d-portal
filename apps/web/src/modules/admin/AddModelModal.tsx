// Initiative 13 Story 20.2 — modal wrapper around AddModelForm so the
// admin "Add Model" flow can fire from the catalog toolbar without
// navigating away from the catalog list. On success the modal closes +
// the caller's onCreated callback handles routing to the new model's
// detail page (the AddModelButton uses navigate({ to: "/catalog/$id" })).

import { useTranslation } from "react-i18next";

import type { ModelDetail } from "@/lib/api-types";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";

import { AddModelForm } from "./AddModelForm";

interface Props {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onCreated: (model: ModelDetail) => void;
}

export function AddModelModal({ open, onOpenChange, onCreated }: Props) {
  const { t } = useTranslation();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* Story 20.2 round-2 Codex P2 — cap modal height + internal scroll
          so submit/cancel stay reachable on short viewports + high zoom. */}
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("admin.models.new.title")}</DialogTitle>
          <DialogDescription>{t("admin.models.new.description")}</DialogDescription>
        </DialogHeader>
        {/* Story 20.2 round-2 Codex P2 — key on open so the form remounts
            (clearing internal state) every time the modal opens. Without
            this, dismissing via X/backdrop/Esc and reopening would show the
            previous draft + leave any pending-submit state visible. */}
        {open && (
          <AddModelForm
            compact
            onSuccess={(model) => {
              onCreated(model);
              onOpenChange(false);
            }}
            onCancel={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
