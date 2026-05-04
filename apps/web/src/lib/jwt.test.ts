import { describe, it, expect } from "vitest";

import { decodeJwtRole } from "./jwt";

function makeJwt(payload: Record<string, unknown>): string {
  // header.payload.signature — only the payload matters for decodeJwtRole.
  // Use base64url encoding without padding (RFC 7515).
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
    .replace(/=+$/, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  const body = btoa(JSON.stringify(payload))
    .replace(/=+$/, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  return `${header}.${body}.signature-not-verified`;
}

describe("decodeJwtRole", () => {
  it("returns admin for admin role claim", () => {
    expect(decodeJwtRole(makeJwt({ sub: "abc", role: "admin" }))).toBe("admin");
  });

  it("returns member for member role claim", () => {
    expect(decodeJwtRole(makeJwt({ sub: "abc", role: "member" }))).toBe("member");
  });

  it("returns agent for agent role claim", () => {
    expect(decodeJwtRole(makeJwt({ sub: "abc", role: "agent" }))).toBe("agent");
  });

  it("returns null for unknown role string", () => {
    expect(decodeJwtRole(makeJwt({ sub: "abc", role: "superuser" }))).toBeNull();
  });

  it("returns null when role claim is missing", () => {
    expect(decodeJwtRole(makeJwt({ sub: "abc" }))).toBeNull();
  });

  it("returns null for malformed token", () => {
    expect(decodeJwtRole("not.a.jwt")).toBeNull();
    expect(decodeJwtRole("only-one-segment")).toBeNull();
    expect(decodeJwtRole("")).toBeNull();
  });
});
