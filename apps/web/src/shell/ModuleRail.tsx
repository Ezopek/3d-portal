import { Link, useLocation } from "@tanstack/react-router";
import { Boxes, Inbox, Layers, Printer, Scroll } from "lucide-react";
import type { ComponentType } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

const MODULES: { key: string; to: string; icon: ComponentType<{ className?: string }> }[] = [
  { key: "catalog", to: "/catalog", icon: Boxes },
  { key: "queue", to: "/queue", icon: Layers },
  { key: "spools", to: "/spools", icon: Scroll },
  { key: "printer", to: "/printer", icon: Printer },
  { key: "requests", to: "/requests", icon: Inbox },
];

export function ModuleRail() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  return (
    <>
      {/* Desktop rail */}
      <nav className="hidden w-60 shrink-0 border-r border-border bg-card lg:flex lg:flex-col">
        <div className="p-4 text-lg font-semibold">{t("app.name")}</div>
        <ul className="flex flex-col gap-1 px-2">
          {MODULES.map(({ key, to, icon: Icon }) => {
            const active = pathname.startsWith(to);
            return (
              <li key={key}>
                <Link
                  to={to}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                    active
                      ? "bg-accent text-accent-foreground"
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
        {MODULES.map(({ key, to, icon: Icon }) => {
          const active = pathname.startsWith(to);
          return (
            <Link
              key={key}
              to={to}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-2 text-xs",
                active ? "text-foreground" : "text-muted-foreground",
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
