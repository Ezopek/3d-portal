import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/ui/dialog";

interface AgentsInfoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Hard-coded prod URLs (not derived from `window.location.origin`) because the
// target consumer is an off-portal AI agent that needs the canonical
// internet-facing address regardless of which host the admin is browsing from
// (LAN IP, dev tunnel, future staging). Update if the prod hostname changes.
const RUNBOOK_URL = "https://3d.ezop.ddns.net/agent-runbook";
const OPENAPI_JSON_URL = "https://3d.ezop.ddns.net/api/openapi.json";
const OPENAPI_DOCS_URL = "https://3d.ezop.ddns.net/api/docs";
const AGENT_TOKEN_PATH = "~/.config/3d-portal/agent.token";

const CURL_RUNBOOK = `curl -fsS ${RUNBOOK_URL} > runbook.md`;
const CURL_OPENAPI = `curl -fsS ${OPENAPI_JSON_URL} > openapi.json`;

function CopyableBlock({
  label,
  command,
  buttonLabel,
  ariaLabel,
  toastCopiedMsg,
  toastErrorMsg,
}: {
  label: string;
  command: string;
  buttonLabel: string;
  ariaLabel: string;
  toastCopiedMsg: string;
  toastErrorMsg: string;
}) {
  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      toast.success(toastCopiedMsg);
    } catch {
      toast.error(toastErrorMsg);
    }
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-foreground/80">{label}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void copy()}
          aria-label={ariaLabel}
          className="shrink-0"
        >
          {buttonLabel}
        </Button>
      </div>
      <pre className="rounded-md border border-border bg-muted/40 p-2 text-xs font-mono text-foreground break-all whitespace-pre-wrap">
        {command}
      </pre>
    </div>
  );
}

export function AgentsInfoDialog({ open, onOpenChange }: AgentsInfoDialogProps) {
  const { t } = useTranslation();

  const buttonLabel = t("agents.dialog.copy_button");
  const copiedToast = t("agents.dialog.copied_toast");
  const errorToast = t("agents.dialog.copy_error_toast");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("agents.dialog.title")}</DialogTitle>
          <DialogDescription>{t("agents.dialog.intro")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <CopyableBlock
            label={t("agents.dialog.section_runbook.label")}
            command={CURL_RUNBOOK}
            buttonLabel={buttonLabel}
            ariaLabel={t("agents.dialog.copy_runbook_aria")}
            toastCopiedMsg={copiedToast}
            toastErrorMsg={errorToast}
          />
          <CopyableBlock
            label={t("agents.dialog.section_openapi.label")}
            command={CURL_OPENAPI}
            buttonLabel={buttonLabel}
            ariaLabel={t("agents.dialog.copy_openapi_aria")}
            toastCopiedMsg={copiedToast}
            toastErrorMsg={errorToast}
          />
          <CopyableBlock
            label={t("agents.dialog.section_credentials.label")}
            command={AGENT_TOKEN_PATH}
            buttonLabel={buttonLabel}
            ariaLabel={t("agents.dialog.copy_credentials_aria")}
            toastCopiedMsg={copiedToast}
            toastErrorMsg={errorToast}
          />
        </div>

        <div className="flex flex-col gap-1 pt-2 text-sm sm:flex-row sm:gap-3">
          <a
            href={RUNBOOK_URL}
            target="_blank"
            rel="noreferrer"
            className="text-primary underline-offset-4 hover:underline"
          >
            {t("agents.dialog.view_runbook")}
          </a>
          <a
            href={OPENAPI_DOCS_URL}
            target="_blank"
            rel="noreferrer"
            className="text-primary underline-offset-4 hover:underline"
          >
            {t("agents.dialog.view_openapi")}
          </a>
        </div>
      </DialogContent>
    </Dialog>
  );
}
