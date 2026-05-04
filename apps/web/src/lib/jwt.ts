import type { Role } from "./api-types";

const KNOWN_ROLES: ReadonlySet<Role> = new Set(["admin", "agent", "member"]);

/**
 * Extract the `role` claim from a JWT without verifying its signature.
 *
 * Use only for UI gates that are double-checked server-side. The token
 * itself was issued by the backend (HS256-signed), so trust here is
 * "good-faith client decoding" — never rely on this for security.
 *
 * Returns null for unknown roles, missing claims, or malformed tokens.
 */
export function decodeJwtRole(token: string): Role | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const payloadSegment = parts[1];
  if (payloadSegment === undefined || payloadSegment === "") return null;
  try {
    // Convert base64url back to base64 for atob.
    const padded = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padding = padded.length % 4;
    const fullyPadded = padding === 0 ? padded : padded + "=".repeat(4 - padding);
    const payload = JSON.parse(atob(fullyPadded)) as Record<string, unknown>;
    const role = payload?.role;
    if (typeof role === "string" && KNOWN_ROLES.has(role as Role)) {
      return role as Role;
    }
    return null;
  } catch {
    return null;
  }
}
