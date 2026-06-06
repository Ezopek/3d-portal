import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

type ActiveTab =
  | "users"
  | "invites"
  | "profiles"
  | "profile-library"
  | "profile-offers"
  | "queues";

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
      <Link
        to="/admin/invites"
        role="tab"
        aria-selected={activeTab === "invites"}
        className={cn(
          baseTab,
          activeTab === "invites"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.invites")}
      </Link>
      <Link
        to="/admin/profiles"
        role="tab"
        aria-selected={activeTab === "profiles"}
        className={cn(
          baseTab,
          activeTab === "profiles"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.profiles")}
      </Link>
      <Link
        to="/admin/profile-library"
        role="tab"
        aria-selected={activeTab === "profile-library"}
        className={cn(
          baseTab,
          activeTab === "profile-library"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.profileLibrary")}
      </Link>
      <Link
        to="/admin/profile-offers"
        role="tab"
        aria-selected={activeTab === "profile-offers"}
        className={cn(
          baseTab,
          activeTab === "profile-offers"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.profileOffers")}
      </Link>
      <Link
        to="/admin/queues"
        role="tab"
        aria-selected={activeTab === "queues"}
        className={cn(
          baseTab,
          activeTab === "queues"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.queues")}
      </Link>
    </nav>
  );
}
