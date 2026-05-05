import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import pl from "./pl.json";

// `initImmediate: false` makes init synchronous so the first paint already
// has resources resolved (we ship them inline, no backend fetch needed).
// Without this, `i18n.t("…")` during the first render returns the literal
// key string — QA round 2 reported `__any_status__` and other raw sentinels
// flashing before the bundle resolved.
void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, pl: { translation: pl } },
    fallbackLng: "pl",
    interpolation: { escapeValue: false },
    initImmediate: false,
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "portal.lang",
    },
  });

export default i18n;
