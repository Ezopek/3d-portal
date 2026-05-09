import { Sentry } from "./instrument";
import "./styles/global.css";

import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";

// `verify-symbolication.sh` (Story 3.1) triggers a deterministic smoke event
// on production by hitting `?__sentry_smoke=<uuid>`. The captureException
// here is a side-effect call — it does NOT throw into the render path, and
// the handler is a no-op without the query param, so visual-regression and
// real users are unaffected. The tag attachment is the verify script's
// search key (`smoke.run_id:<uuid>` against GlitchTip's REST issues
// endpoint) — drift breaks the verify ritual silently.
const smokeRunId = new URLSearchParams(window.location.search).get("__sentry_smoke");
if (smokeRunId) {
  Sentry.captureException(new Error(`smoke ${smokeRunId}`), {
    tags: { "smoke.run_id": smokeRunId },
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
