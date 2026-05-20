import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { InviteRoleRequest, InviteTTLPreset } from "@/lib/api-types";
import { Button } from "@/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";

interface Props {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  pending?: boolean;
  onConfirm: (payload: {
    role: InviteRoleRequest;
    ttl_preset: InviteTTLPreset;
  }) => void;
}

/**
 * Story 8.6 — admin Invite generation modal. The role select intentionally
 * omits the `agent` option entirely (backend rejects it at the schema layer
 * via `InviteRoleRequestLiteral = Literal["member", "admin"]`). The TTL
 * field is a finite radio-button choice over the 4 backend presets per
 * Decision B verbatim — no custom `ttl_seconds` input is exposed.
 */
export function GenerateInviteModal({
  open,
  onOpenChange,
  pending = false,
  onConfirm,
}: Props) {
  const { t } = useTranslation();
  const [selectedRole, setSelectedRole] = useState<InviteRoleRequest>("member");
  const [selectedTtlPreset, setSelectedTtlPreset] =
    useState<InviteTTLPreset>("SEVEN_DAYS");

  useEffect(() => {
    if (open) {
      setSelectedRole("member");
      setSelectedTtlPreset("SEVEN_DAYS");
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("admin.invites.generate.title")}</DialogTitle>
          <DialogDescription>
            {t("admin.invites.generate.description")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium">
              {t("admin.invites.generate.role_label")}
            </span>
            <select
              value={selectedRole}
              onChange={(e) =>
                setSelectedRole(e.target.value as InviteRoleRequest)
              }
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              disabled={pending}
              aria-label={t("admin.invites.generate.role_label")}
            >
              <option value="member">
                {t("admin.invites.generate.role_member")}
              </option>
              <option value="admin">
                {t("admin.invites.generate.role_admin")}
              </option>
            </select>
          </label>
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium">
              {t("admin.invites.generate.ttl_label")}
            </span>
            <select
              value={selectedTtlPreset}
              onChange={(e) =>
                setSelectedTtlPreset(e.target.value as InviteTTLPreset)
              }
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              disabled={pending}
              aria-label={t("admin.invites.generate.ttl_label")}
            >
              <option value="ONE_DAY">
                {t("admin.invites.generate.ttl_one_day")}
              </option>
              <option value="THREE_DAYS">
                {t("admin.invites.generate.ttl_three_days")}
              </option>
              <option value="SEVEN_DAYS">
                {t("admin.invites.generate.ttl_seven_days")}
              </option>
              <option value="THIRTY_DAYS">
                {t("admin.invites.generate.ttl_thirty_days")}
              </option>
            </select>
          </label>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            {t("admin.invites.generate.cancel")}
          </Button>
          <Button
            onClick={() =>
              onConfirm({
                role: selectedRole,
                ttl_preset: selectedTtlPreset,
              })
            }
            disabled={pending}
          >
            {pending
              ? t("admin.invites.generate.submitting")
              : t("admin.invites.generate.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
