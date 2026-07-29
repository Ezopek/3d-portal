import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

type ActiveTab =
  | "users"
  | "invites"
  | "profile-library"
  | "profile-offers"
  | "queues"
  | "tag-groups"
  | "categories";

export function AdminTabs({ activeTab }: { activeTab: ActiveTab }) {
  const { t } = useTranslation();
  // `shrink-0` + `whitespace-nowrap` keep each tab intact; the ROW scrolls
  // instead of the document. Story 52.2 added the seventh tab, and the row was
  // already wider than a Pixel 5 viewport at six — an overflowing document makes
  // mobile Chrome expand the LAYOUT viewport away from the visual one, which is
  // exactly the divergence Story 48.1 documents (measured here: innerWidth 675
  // against a 393 CSS-px device). Containing the overflow inside the nav keeps
  // every admin page's document within the viewport.
  const baseTab =
    "shrink-0 whitespace-nowrap px-3 py-2 text-sm font-medium border-b-2 transition-colors";
  return (
    <nav
      role="tablist"
      aria-label={t("admin.tabs.nav_aria_label")}
      className="flex gap-2 overflow-x-auto border-b border-border"
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
      <Link
        to="/admin/tag-groups"
        role="tab"
        aria-selected={activeTab === "tag-groups"}
        className={cn(
          baseTab,
          activeTab === "tag-groups"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.tagGroups")}
      </Link>
      <Link
        to="/admin/categories"
        role="tab"
        aria-selected={activeTab === "categories"}
        className={cn(
          baseTab,
          activeTab === "categories"
            ? "border-primary text-foreground"
            : "border-transparent text-muted-foreground hover:text-foreground",
        )}
      >
        {t("admin.tabs.categories")}
      </Link>
    </nav>
  );
}
