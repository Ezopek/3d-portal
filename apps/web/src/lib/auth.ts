const KEY = "portal.token";
const EXP_KEY = "portal.token.exp";

export interface StoredToken {
  token: string;
  expiresAt: number;
}

export function readToken(): StoredToken | null {
  const t = localStorage.getItem(KEY);
  const exp = Number(localStorage.getItem(EXP_KEY) ?? 0);
  if (t === null || Number.isNaN(exp) || exp < Date.now()) return null;
  return { token: t, expiresAt: exp };
}

export function writeToken(token: string, expiresInSeconds: number): void {
  localStorage.setItem(KEY, token);
  localStorage.setItem(EXP_KEY, String(Date.now() + expiresInSeconds * 1000));
}

export function clearToken(): void {
  localStorage.removeItem(KEY);
  localStorage.removeItem(EXP_KEY);
}

export function isAdmin(): boolean {
  // Decode the role claim from the stored JWT instead of treating any logged-in
  // user as admin — the API has both admin and member roles and the UI gate
  // should match the API guard, not just "has a token".
  const stored = readToken();
  if (stored === null) return false;
  try {
    const payload = JSON.parse(atob(stored.token.split(".")[1] ?? ""));
    return payload?.role === "admin";
  } catch {
    return false;
  }
}
