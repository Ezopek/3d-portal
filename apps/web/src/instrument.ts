import * as Sentry from "@sentry/react";

const dsn = import.meta.env.VITE_SENTRY_DSN;

if (typeof dsn === "string" && dsn !== "") {
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_ENVIRONMENT ?? "dev",
    release: import.meta.env.VITE_PORTAL_VERSION ?? "0.1.0",
    sampleRate: 1.0,
    tracesSampleRate: 0,
  });
  Sentry.setTag("service", "web");
}

export { Sentry };
