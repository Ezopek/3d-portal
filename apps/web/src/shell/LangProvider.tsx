import "@/locales/i18n";

import type { ReactNode } from "react";

export function LangProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
