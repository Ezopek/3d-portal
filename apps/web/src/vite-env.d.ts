/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_ENVIRONMENT?: string;
  readonly VITE_BUILD_HOST?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare const __GIT_COMMIT__: string;
declare const __BUILD_TIME__: string;
declare const __BUILD_HOST__: string;
declare const __PKG_VERSION__: string;
