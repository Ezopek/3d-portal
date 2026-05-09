import { Sentry } from "./instrument";
import "./styles/global.css";

import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";

// `verify-symbolication.sh` (Story 3.1) triggers a deterministic smoke event
// on production by hitting `?__sentry_smoke=<uuid>` via headless chrome.
// captureException is a side-effect call — does NOT throw into the render
// path, and the handler is a no-op without the query param so visual
// regression + real users are unaffected. The tag attachment is the verify
// script's search key (`smoke.run_id:<uuid>` against GlitchTip's REST
// issues endpoint) — drift breaks the verify ritual silently.
// `flush(2000)` is necessary because headless chrome closes shortly after
// load; without an explicit flush the SDK transport may not complete
// before the browser exits.
const smokeRunId = new URLSearchParams(window.location.search).get("__sentry_smoke");
if (smokeRunId) {
  Sentry.captureException(new Error(`smoke ${smokeRunId}`), {
    tags: { "smoke.run_id": smokeRunId },
  });
  void Sentry.flush(2000);
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
