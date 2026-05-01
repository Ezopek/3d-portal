import { useTranslation } from "react-i18next";

import { LangToggle } from "./LangToggle";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";

export function TopBar() {
  const { t } = useTranslation();
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur">
      <div className="flex flex-1 items-center gap-3">
        {/* On <lg the desktop ModuleRail title is hidden — surface app name here.
            Phase 8 will replace this with a breadcrumb portal. */}
        <span className="text-base font-semibold lg:hidden">{t("app.name")}</span>
      </div>
      <ThemeToggle />
      <LangToggle />
      <UserMenu />
    </header>
  );
}
