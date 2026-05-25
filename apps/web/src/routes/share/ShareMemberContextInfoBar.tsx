import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Info, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

// Initiative 18 Story 30.2 (Decision AC) — dismissible info-bar surfaced
// at the top of MemberShareView's main content. Signals to the B5 recipient
// that they arrived via a share link (so /share/<token> is not their
// canonical bookmark) and offers an explicit affordance to switch to the
// canonical /catalog/$id URL.
//
// Dismissal: sessionStorage keyed by `share-context-dismissed:<modelId>`.
// Per-model scope (different share for a different model in the same
// session re-shows). Per-session scope (next session re-shows — recipient
// may have forgotten the context).
//
// sessionStorage unavailable (private browsing strict mode, embedded
// WebView): try/catch fail-open — info-bar always renders + dismiss
// works in-memory for the component lifetime.

const KEY_PREFIX = "share-context-dismissed:";

function _readDismissed(modelId: string): boolean {
  try {
    return (
      typeof window !== "undefined" &&
      window.sessionStorage.getItem(KEY_PREFIX + modelId) !== null
    );
  } catch {
    return false;
  }
}

function _writeDismissed(modelId: string): void {
  try {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(KEY_PREFIX + modelId, "1");
    }
  } catch {
    // in-memory fall-back via setDismissed handled by the caller
  }
}

export function ShareMemberContextInfoBar({ modelId }: { modelId: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [dismissed, setDismissed] = useState<boolean>(() => _readDismissed(modelId));

  // Re-check dismissed state when modelId changes (different share link
  // for a different model surfaced in the same session).
  useEffect(() => {
    setDismissed(_readDismissed(modelId));
  }, [modelId]);

  if (dismissed) return null;

  const handleDismiss = () => {
    _writeDismissed(modelId);
    setDismissed(true);
  };

  // Round-7 (Codex P1 follow-up) — evict the canonical model cache
  // SYNCHRONOUSLY before navigating to /catalog/$id. Without this, the
  // catalog route's `useModel` observer can subscribe to the share-
  // populated cache entry BEFORE MemberShareView's unmount-cleanup
  // useEffect fires, then sticks to the cached snapshot for up to 30s
  // because removeQueries doesn't invalidate already-mounted observers.
  // Doing the evict here guarantees the catalog mount sees an empty
  // cache → forced fresh GET. (MemberShareView's unmount-cleanup stays
  // in place for the browser-back / direct-URL navigation paths.)
  const handleOpenInCatalog = () => {
    qc.removeQueries({ queryKey: ["sot", "models", modelId] });
    void navigate({ to: "/catalog/$id", params: { id: modelId } });
  };

  return (
    <div
      role="status"
      className="mb-4 flex items-center justify-between gap-3 rounded-md border border-border bg-muted/50 px-3 py-2 text-sm"
    >
      <div className="flex items-center gap-2">
        <Info className="size-4 shrink-0 text-muted-foreground" />
        <span>{t("share.member_context.banner")}</span>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleOpenInCatalog}
          className="text-sm font-medium underline-offset-4 hover:underline"
        >
          {t("share.member_context.open_in_catalog")}
        </button>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label={t("share.member_context.dismiss_aria")}
          className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      </div>
    </div>
  );
}
