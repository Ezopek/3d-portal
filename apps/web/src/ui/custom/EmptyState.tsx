import { useTranslation } from "react-i18next";

export function EmptyState({ messageKey }: { messageKey: string }) {
  const { t } = useTranslation();
  return (
    <div className="grid place-items-center p-12 text-center">
      <p className="text-sm text-muted-foreground">{t(messageKey)}</p>
    </div>
  );
}
