import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card, CardDescription, CardTitle } from "@/ui/card";

/**
 * Initiative 7 Story 12.4 — flat list-of-cards hub at /settings (architecture
 * Decision Q). Each card routes to a sibling settings route:
 *   - /settings/profile  (Story 12.3)
 *   - /settings/2fa      (Init 5)
 *   - /settings/sessions (Init 5)
 *
 * The shell-level AuthGate (AppShell.tsx Decision O) handles the anonymous
 * redirect; no per-route wrapper is required.
 */
interface HubEntry {
  to: "/settings/profile" | "/settings/2fa" | "/settings/sessions" | "/settings/share-links";
  titleKey: string;
  descriptionKey: string;
}

const HUB_ENTRIES: HubEntry[] = [
  {
    to: "/settings/profile",
    titleKey: "settings.hub.profile.card_title",
    descriptionKey: "settings.hub.profile.card_description",
  },
  {
    to: "/settings/2fa",
    titleKey: "settings.hub.2fa.card_title",
    descriptionKey: "settings.hub.2fa.card_description",
  },
  {
    to: "/settings/sessions",
    titleKey: "settings.hub.sessions.card_title",
    descriptionKey: "settings.hub.sessions.card_description",
  },
  {
    to: "/settings/share-links",
    titleKey: "settings.hub.share_links.card_title",
    descriptionKey: "settings.hub.share_links.card_description",
  },
];

function SettingsHubPage() {
  const { t } = useTranslation();

  return (
    <div className="mx-auto max-w-2xl space-y-3 p-6">
      <header className="space-y-2 pb-2">
        <h1 className="text-xl font-semibold">{t("settings.hub.title")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("settings.hub.description")}
        </p>
      </header>

      <nav aria-label={t("settings.hub.title")} className="space-y-3">
        {HUB_ENTRIES.map((entry) => (
          <Link
            key={entry.to}
            to={entry.to}
            className="block rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <Card
              size="sm"
              className="flex-row items-center justify-between gap-4 px-4 py-4 transition-colors hover:bg-accent"
            >
              <div className="flex flex-col gap-1">
                <CardTitle>{t(entry.titleKey)}</CardTitle>
                <CardDescription>{t(entry.descriptionKey)}</CardDescription>
              </div>
              <ChevronRight
                className="size-5 shrink-0 text-muted-foreground"
                aria-hidden
              />
            </Card>
          </Link>
        ))}
      </nav>
    </div>
  );
}

export const Route = createFileRoute("/settings/")({
  // Shell-level AuthGate (AppShell.tsx Decision O) handles the anonymous
  // redirect — anonymous load lands on /login?next=%2Fsettings.
  component: SettingsHubPage,
});
