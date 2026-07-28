import { Link, useLocation } from "@tanstack/react-router";
import { Boxes, Inbox, Layers, Printer, Scroll } from "lucide-react";
import type { ComponentType } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

const MODULES: {
  key: string;
  to: string;
  icon: ComponentType<{ className?: string }>;
  /** Extra path prefixes this module also owns, beyond `to` (Story 51.2 D-8). */
  alsoOwns?: readonly string[];
}[] = [
  // `/categories/{slug}` is the catalogue's canonical browse URL since Story
  // 51.2. Without this, `pathname.startsWith(to)` leaves NO module row active
  // there on desktop AND mobile — a "where am I" regression the new route would
  // otherwise introduce. This adds, removes and renames NO tab: the tab set,
  // icons, labels and both geometries are untouched, so Story 51.3's `Ask First`
  // boundary (which is about the mobile tab SET) is undisturbed (AC-17).
  { key: "catalog", to: "/catalog", icon: Boxes, alsoOwns: ["/categories"] },
  { key: "queue", to: "/queue", icon: Layers },
  { key: "spools", to: "/spools", icon: Scroll },
  { key: "printer", to: "/printer", icon: Printer },
  { key: "requests", to: "/requests", icon: Inbox },
];

function isModuleActive(
  pathname: string,
  to: string,
  alsoOwns?: readonly string[],
): boolean {
  return (
    pathname.startsWith(to) ||
    (alsoOwns?.some((p) => pathname.startsWith(p)) ?? false)
  );
}

export function ModuleRail() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  return (
    <>
      {/* Desktop rail */}
      <nav className="hidden w-60 shrink-0 border-r border-border bg-card lg:flex lg:flex-col">
        <div className="p-4 text-lg font-semibold">{t("app.name")}</div>
        <ul className="flex flex-col gap-1 px-2">
          {MODULES.map(({ key, to, icon: Icon, alsoOwns }) => {
            const active = isModuleActive(pathname, to, alsoOwns);
            return (
              <li key={key}>
                <Link
                  to={to}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                    active
                      ? "bg-primary/10 text-foreground font-medium ring-1 ring-inset ring-primary"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <Icon className="size-4" />
                  <span>{t(`modules.${key}`)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      {/* Mobile bottom bar */}
      <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-card lg:hidden">
        {MODULES.map(({ key, to, icon: Icon, alsoOwns }) => {
          const active = isModuleActive(pathname, to, alsoOwns);
          return (
            <Link
              key={key}
              to={to}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-2 text-xs",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className="size-5" />
              <span>{t(`modules.${key}`)}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
