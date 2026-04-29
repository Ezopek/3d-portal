import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "@/lib/api";
import { Button } from "@/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/ui/dialog";
import { Input } from "@/ui/input";

interface Props {
  modelId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ShareResponse { token: string; url: string; expires_at: string }

export function ShareDialog({ modelId, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const [hours, setHours] = useState(72);
  const [result, setResult] = useState<ShareResponse | null>(null);

  async function create() {
    const r = await api<ShareResponse>("/admin/share", {
      method: "POST",
      body: JSON.stringify({ model_id: modelId, expires_in_hours: hours }),
    }, { authenticated: true });
    setResult(r);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("catalog.actions.share")}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <label className="grid gap-1 text-sm">
            <span>{t("catalog.share.expires_in_hours")}</span>
            <Input type="number" value={hours} onChange={(e) => setHours(Number(e.target.value))} min={1} max={720} />
          </label>
          {result === null ? (
            <Button onClick={() => void create()}>{t("catalog.actions.share")}</Button>
          ) : (
            <>
              <Input readOnly value={`${window.location.origin}${result.url}`} />
              <p className="text-xs text-muted-foreground">{t("catalog.share.expires_at")}: {result.expires_at}</p>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
