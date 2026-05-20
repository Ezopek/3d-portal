import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

type ActiveTab = "users" | "invites";

export function AdminTabs({ activeTab }: { activeTab: ActiveTab }) {
  const { t } = useTranslation();
  const baseTab =
    "px-3 py-2 text-sm font-medium border-b-2 transition-colors";
  return (
    <nav
      role="tablist"
      aria-label={t("admin.tabs.users")}
      className="flex gap-2 border-b border-border"
    >
      <Link
        to="/admin/users"
        role="tab"
        aria-selected={activeTab === "users"}
        className={cn(
          baseTab,
          activeTab === "users"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.users")}
      </Link>
      <span
        role="tab"
        aria-selected={activeTab === "invites"}
        aria-disabled="true"
        tabIndex={-1}
        title={t("admin.tabs.invites_coming_soon")}
        className={cn(
          baseTab,
          "border-transparent cursor-not-allowed text-muted-foreground opacity-50",
        )}
        onClick={(e) => e.preventDefault()}
      >
        {t("admin.tabs.invites")}
      </span>
    </nav>
  );
}
