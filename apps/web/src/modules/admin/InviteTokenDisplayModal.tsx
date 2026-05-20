import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Role } from "@/lib/api-types";
import { Button } from "@/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";
import { Input } from "@/ui/input";

interface Props {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  role: Role;
  registrationUrl: string;
  expiresAt: string;
}

/**
 * Story 8.6 — cleartext-token-once modal for the admin Invite generation
 * surface. Sibling implementation of `ResetLinkDisplayModal` (Story 8.5):
 * the operator copies the registration URL once and delivers it
 * out-of-band; closing the modal without copying forces the operator to
 * generate a fresh invite (Decision B verbatim "cleartext token never
 * returned in any list-invites response").
 */
export function InviteTokenDisplayModal({
  open,
  onOpenChange,
  role,
  registrationUrl,
  expiresAt,
}: Props) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const formattedExpiry = new Date(expiresAt).toLocaleString("pl-PL");

  // Backend returns relative path (`/register?token=...`); out-of-band
  // delivery needs absolute URL with origin so the recipient can
  // paste-and-open without manual prefix. Mirrors Story 8.5
  // `ResetLinkDisplayModal` P2 fix-up verbatim.
  const absoluteUrl = (() => {
    try {
      return new URL(registrationUrl, window.location.origin).toString();
    } catch {
      return registrationUrl;
    }
  })();

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setCopied(true);
    } catch {
      // Clipboard can fail in restricted contexts; the URL stays
      // visible in the read-only input so the operator can still copy
      // manually — no banner needed.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t("admin.invites.token_modal.title", { role })}
          </DialogTitle>
          <DialogDescription>
            {t("admin.invites.token_modal.body", {
              expires_at: formattedExpiry,
            })}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2 py-2">
          <Input
            readOnly
            value={absoluteUrl}
            aria-label={t("admin.invites.token_modal.title", { role })}
          />
          <Button type="button" variant="outline" onClick={handleCopy}>
            {copied
              ? t("admin.invites.token_modal.copied_label")
              : t("admin.invites.token_modal.copy_button")}
          </Button>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            {t("admin.invites.token_modal.done_button")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
