import i18n from "@/locales/i18n";

import { useEffect, useState, type ReactNode } from "react";

/**
 * Render children only after i18next has finished initializing.
 *
 * Resources are bundled inline and `initImmediate: false` makes the first
 * `init()` call synchronous, so by the time React mounts this provider
 * `i18n.isInitialized` is almost always already `true`. This effect is a
 * defensive fallback for the rare case (HMR, future async resources) where
 * the bundle isn't ready yet — without it, components like FilterRibbon
 * would briefly render raw sentinel keys (`__any_status__`) on first paint.
 */
export function LangProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState<boolean>(i18n.isInitialized);

  useEffect(() => {
    if (i18n.isInitialized) {
      if (!ready) setReady(true);
      return;
    }
    function handle() {
      setReady(true);
    }
    i18n.on("initialized", handle);
    return () => {
      i18n.off("initialized", handle);
    };
  }, [ready]);

  if (!ready) return null;
  return <>{children}</>;
}
