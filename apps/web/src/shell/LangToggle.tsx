import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

const LANGS = ["pl", "en"] as const;
type Lang = (typeof LANGS)[number];

export function LangToggle() {
  const { i18n } = useTranslation();
  const current: Lang = i18n.language.startsWith("pl") ? "pl" : "en";
  return (
    <div
      role="group"
      aria-label="Language"
      className="inline-flex overflow-hidden rounded-md border border-border"
    >
      {LANGS.map((lang) => {
        const active = lang === current;
        return (
          <button
            key={lang}
            type="button"
            aria-pressed={active}
            onClick={() => {
              if (!active) void i18n.changeLanguage(lang);
            }}
            className={cn(
              "px-2 py-1 text-xs font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {lang.toUpperCase()}
          </button>
        );
      })}
    </div>
  );
}
