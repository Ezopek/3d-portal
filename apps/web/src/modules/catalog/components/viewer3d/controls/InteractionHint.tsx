import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const STORAGE_KEY = "viewer3d:hint_dismissed";

/**
 * One-shot overlay that teaches first-time users the canvas controls.
 * Persists dismissal in localStorage so it never appears twice.
 */
export function InteractionHint() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) !== "1") setVisible(true);
    } catch {
      // localStorage may be unavailable in private mode — show the hint once
      // per page load and rely on the same-tab dismiss.
      setVisible(true);
    }
  }, []);

  function dismiss() {
    setVisible(false);
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* ignore */
    }
  }

  if (!visible) return null;
  return (
    <div className="pointer-events-auto absolute bottom-2 left-1/2 z-20 flex max-w-[90%] -translate-x-1/2 items-center gap-2 rounded-md bg-background/85 px-2.5 py-1 text-[11px] text-muted-foreground shadow-md backdrop-blur">
      <span>{t("viewer3d.hint")}</span>
      <button
        type="button"
        aria-label={t("viewer3d.hint_dismiss")}
        onClick={dismiss}
        className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:bg-accent hover:text-foreground"
      >
        <X className="size-3" aria-hidden />
      </button>
    </div>
  );
}
