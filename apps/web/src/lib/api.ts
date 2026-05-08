import { refreshAccessToken } from "./refresh";

const BASE = "/api";

export class ApiError extends Error {
  constructor(public status: number, public body: unknown, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  return _api<T>(path, init, /* canRetry */ true);
}

async function _api<T>(path: string, init: RequestInit, canRetry: boolean): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("X-Portal-Client", "web");

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && canRetry) {
    const body = await response.clone().json().catch(() => ({}));
    const detail = (body as { detail?: string })?.detail;
    if (detail === "access_expired" || detail === "missing_access") {
      const ok = await refreshAccessToken();
      if (ok) {
        return _api<T>(path, init, /* canRetry */ false);
      }
    }
  }
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      /* ignore */
    }
    throw new ApiError(response.status, body, `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
