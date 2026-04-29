import { useTranslation } from "react-i18next";

import { Button } from "@/ui/button";

export function LangToggle() {
  const { i18n } = useTranslation();
  const next = i18n.language.startsWith("pl") ? "en" : "pl";
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => void i18n.changeLanguage(next)}
      aria-label="Toggle language"
    >
      {next.toUpperCase()}
    </Button>
  );
}
