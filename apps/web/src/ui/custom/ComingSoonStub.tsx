import { Construction } from "lucide-react";
import { useTranslation } from "react-i18next";

export function ComingSoonStub({ moduleKey }: { moduleKey: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <Construction
        aria-hidden
        className="size-16 text-muted-foreground/40"
      />
      <h2 className="text-2xl font-semibold">{t(`modules.${moduleKey}`)}</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        {t("common.coming_soon")}
      </p>
    </div>
  );
}
