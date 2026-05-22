// Initiative 10 Story 16.3 — member-side share-link generation dialog.
//
// Member or admin opens this dialog from the model-detail page; picks a TTL
// preset (1d / 3d / 7d — hard-capped at 7 days per operator decision §1.1
// and Pydantic constraint in apps/api/app/modules/share/models.py); POSTs
// to /api/admin/share; renders the generated link with a copy-to-clipboard
// button so it can be shared out-of-band (Slack / email / SMS).

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { createShareLink, type ShareTtlPreset } from "@/lib/share-api";
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
  modelId: string;
  modelName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const TTL_PRESETS: { value: ShareTtlPreset; labelKey: string }[] = [
  { value: 1, labelKey: "share.dialog.ttl_1d" },
  { value: 3, labelKey: "share.dialog.ttl_3d" },
  { value: 7, labelKey: "share.dialog.ttl_7d" },
];

export function ShareLinkDialog({ modelId, modelName, open, onOpenChange }: Props) {
  const { t } = useTranslation();
  const [ttl, setTtl] = useState<ShareTtlPreset>(7);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => createShareLink(modelId, ttl),
    onSuccess: (data) => {
      const fullUrl = `${window.location.origin}${data.url}`;
      setGeneratedUrl(fullUrl);
    },
    onError: () => {
      toast.error(t("share.dialog.errors.create_failed"));
    },
  });

  const handleCopy = async () => {
    if (generatedUrl === null) return;
    try {
      await navigator.clipboard.writeText(generatedUrl);
      toast.success(t("share.dialog.copied"));
    } catch {
      toast.error(t("share.dialog.errors.copy_failed"));
    }
  };

  const handleClose = (next: boolean) => {
    if (!next) {
      setGeneratedUrl(null);
      setTtl(7);
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("share.dialog.title")}</DialogTitle>
          <DialogDescription>
            {t("share.dialog.description", { model: modelName })}
          </DialogDescription>
        </DialogHeader>

        {generatedUrl === null ? (
          <div className="space-y-4">
            <fieldset>
              <legend className="mb-2 text-sm font-medium">
                {t("share.dialog.ttl_label")}
              </legend>
              <div className="flex gap-2">
                {TTL_PRESETS.map((preset) => (
                  <label
                    key={preset.value}
                    className={`flex flex-1 cursor-pointer items-center justify-center rounded border px-3 py-2 text-sm ${
                      ttl === preset.value
                        ? "border-primary bg-primary/10 font-medium"
                        : "border-border hover:bg-accent"
                    }`}
                  >
                    <input
                      type="radio"
                      name="share-ttl"
                      value={preset.value}
                      checked={ttl === preset.value}
                      onChange={() => setTtl(preset.value)}
                      className="sr-only"
                    />
                    {t(preset.labelKey)}
                  </label>
                ))}
              </div>
            </fieldset>
            <p className="text-xs text-muted-foreground">
              {t("share.dialog.notice_anonymous_readonly")}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <label className="block text-sm font-medium">
              {t("share.dialog.generated_url_label")}
            </label>
            <input
              type="text"
              readOnly
              value={generatedUrl}
              onFocus={(e) => e.currentTarget.select()}
              className="w-full rounded border border-border bg-muted/30 px-3 py-2 font-mono text-xs"
              aria-label={t("share.dialog.generated_url_label")}
            />
            <p className="text-xs text-muted-foreground">
              {t("share.dialog.notice_share_oob")}
            </p>
          </div>
        )}

        <DialogFooter>
          {generatedUrl === null ? (
            <>
              <Button variant="outline" onClick={() => handleClose(false)}>
                {t("common.cancel")}
              </Button>
              <Button
                onClick={() => mutation.mutate()}
                disabled={mutation.isPending}
              >
                {mutation.isPending
                  ? t("share.dialog.generating")
                  : t("share.dialog.generate")}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => handleClose(false)}>
                {t("common.close")}
              </Button>
              <Button onClick={handleCopy}>{t("share.dialog.copy")}</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
