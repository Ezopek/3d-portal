import { useState } from "react";
import { useTranslation } from "react-i18next";

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
  email: string;
  resetUrl: string;
  expiresAt: string;
}

/**
 * Story 8.5 — cleartext-token-once modal for the admin-issued password-reset
 * link surface. Mirrors the Story 6.3 invite-token "shown only once" UX:
 * the operator copies the URL and delivers it out-of-band; closing the
 * modal without copying forces the operator to issue a fresh link.
 */
export function ResetLinkDisplayModal({
  open,
  onOpenChange,
  email,
  resetUrl,
  expiresAt,
}: Props) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const formattedExpiry = new Date(expiresAt).toLocaleString("pl-PL");

  // Codex P2 fix-up: backend returns relative path; out-of-band delivery
  // (SMS/Messenger/personal email) needs an absolute URL with origin so
  // the recipient can paste-and-open without manual prefix. Resolve via
  // URL constructor against window.location.origin.
  const absoluteUrl = (() => {
    try {
      return new URL(resetUrl, window.location.origin).toString();
    } catch {
      return resetUrl;
    }
  })();

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setCopied(true);
    } catch {
      // Clipboard write can fail in restricted contexts (older browsers,
      // missing permission). The operator still has the visible URL in
      // the read-only input — no need to surface an error banner.
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t("admin.users.reset_link.modal_title", { email })}
          </DialogTitle>
          <DialogDescription>
            {t("admin.users.reset_link.modal_body", {
              expires_at: formattedExpiry,
            })}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-2 py-2">
          <Input
            readOnly
            value={absoluteUrl}
            aria-label={t("admin.users.reset_link.modal_title", { email })}
          />
          <Button type="button" variant="outline" onClick={handleCopy}>
            {copied
              ? t("admin.users.reset_link.copied_label")
              : t("admin.users.reset_link.copy_button")}
          </Button>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            {t("admin.users.reset_link.done_button")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
