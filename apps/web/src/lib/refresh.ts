const BASE = "/api";

let inFlight: Promise<boolean> | null = null;

export function refreshAccessToken(): Promise<boolean> {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    try {
      const r = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "X-Portal-Client": "web" },
      });
      return r.ok;
    } catch {
      return false;
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}
