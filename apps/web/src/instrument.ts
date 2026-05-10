import * as Sentry from "@sentry/react";

import { RELEASE } from "@/release";

import { applyBeforeSendFilters } from "./instrument-filters";

const dsn = import.meta.env.VITE_SENTRY_DSN;

if (typeof dsn === "string" && dsn !== "") {
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_ENVIRONMENT ?? "dev",
    release: RELEASE,
    sampleRate: 1.0,
    tracesSampleRate: 0,
    beforeSend: applyBeforeSendFilters,
  });
  Sentry.setTag("service", "web");
  // Static identity tags (Story 2.2, architecture Decision G). Attached once
  // at SDK init; values resolve at build time via Vite `define` (`__GIT_COMMIT__`,
  // `__BUILD_TIME__`, `__BUILD_HOST__`) plus runtime env overrides for host /
  // environment. Dotted-name keys align with observability-logging-contract.md.
  Sentry.setTag("service.version", RELEASE);
  Sentry.setTag("host.name", import.meta.env.VITE_BUILD_HOST ?? __BUILD_HOST__);
  Sentry.setTag("deployment.environment", import.meta.env.VITE_ENVIRONMENT ?? "production");
  Sentry.setTag("git.commit", __GIT_COMMIT__);
  Sentry.setTag("build.time", __BUILD_TIME__);
}

export { Sentry };
