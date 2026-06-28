import { PackageOpen, WifiOff } from "lucide-react";
import { EmptyState } from "portal-web";

export function NoResults() {
  return (
    <EmptyState
      messageKey="catalog.empty"
      icon={<PackageOpen className="size-10" />}
      action={{ labelKey: "Wyczyść filtry", onClick: () => {} }}
    />
  );
}

export function ErrorTone() {
  return (
    <EmptyState
      tone="error"
      messageKey="Nie udało się wczytać modeli. Spróbuj ponownie."
      icon={<WifiOff className="size-10" />}
    />
  );
}
