import { useNavigate } from "@tanstack/react-router";
import { LogIn } from "lucide-react";
import { useTranslation } from "react-i18next";

// Initiative 18 Story 30.3 / FR18-CHROME-ADDITIONS-1 — Sign in affordance
// rendered in the anonymous share-view header. Navigates to /login carrying
// the original /share/<token> as `next` so post-login lands the recipient
// back on the share link they came from. Story 30.1 hardened
// `validateSearch` accepts this path shape (RU-1 happy case).
export function SignInButton({ token }: { token: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() =>
        void navigate({
          to: "/login",
          search: { next: `/share/${token}` },
          replace: false,
        })
      }
      aria-label={t("share.view.signin_aria")}
      className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
    >
      <LogIn className="size-4" />
      {t("share.view.signin_cta")}
    </button>
  );
}
