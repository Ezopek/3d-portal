import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";
import pl from "@/locales/pl.json";

function flat(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const full = prefix ? `${prefix}.${k}` : k;
    return typeof v === "object" && v !== null
      ? flat(v as Record<string, unknown>, full)
      : [full];
  });
}

describe("i18n key parity", () => {
  it("en and pl have identical key sets", () => {
    const enKeys = new Set(flat(en));
    const plKeys = new Set(flat(pl));
    expect([...enKeys].filter((k) => !plKeys.has(k))).toEqual([]);
    expect([...plKeys].filter((k) => !enKeys.has(k))).toEqual([]);
  });
});
