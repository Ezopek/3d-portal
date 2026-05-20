import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AdminUser, Role } from "@/lib/api-types";
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
  target: AdminUser | null;
  pending?: boolean;
  onConfirm: (newRole: Role) => void;
}

/**
 * Story 8.3 — role-change modal for the admin Users tab. The `agent` option
 * is always disabled in the select: per architecture.md:1049, the agent
 * service account is created by the bootstrap script, not the admin panel.
 * The backend mirrors this guard with the `cannot_promote_to_agent` 400.
 */
export function ChangeRoleModal({
  open,
  onOpenChange,
  target,
  pending = false,
  onConfirm,
}: Props) {
  const { t } = useTranslation();
  const [selectedRole, setSelectedRole] = useState<Role>(target?.role ?? "member");

  useEffect(() => {
    if (target) {
      setSelectedRole(target.role);
    }
  }, [target]);

  if (!target) return null;

  const isNoop = selectedRole === target.role;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t("admin.users.change_role.title", { email: target.email })}
          </DialogTitle>
          <DialogDescription>
            {t("admin.users.change_role.description")}
          </DialogDescription>
        </DialogHeader>
        <div className="py-2">
          <label className="flex flex-col gap-2 text-sm">
            <span className="font-medium">
              {t("admin.users.change_role.title", { email: target.email })}
            </span>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value as Role)}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              disabled={pending}
              aria-label={t("admin.users.actions.change_role")}
            >
              <option value="admin">
                {t("admin.users.change_role.option_admin")}
              </option>
              <option value="member">
                {t("admin.users.change_role.option_member")}
              </option>
              <option value="agent" disabled>
                {t("admin.users.change_role.option_agent")}
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
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() => onConfirm(selectedRole)}
            disabled={pending || isNoop}
          >
            {t("common.confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
