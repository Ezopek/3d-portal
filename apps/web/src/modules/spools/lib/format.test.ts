import { describe, expect, it } from "vitest";

import { formatTimeOfDay, formatWeight, minutesSince } from "./format";

describe("formatWeight", () => {
  it("renders null as em dash", () => {
    expect(formatWeight(null)).toBe("—");
  });

  it("renders grams when below 1 kg", () => {
    expect(formatWeight(499)).toBe("499 g");
    expect(formatWeight(138.9)).toBe("139 g");
  });

  it("renders kg with 2 decimals when at or above 1 kg", () => {
    expect(formatWeight(1000)).toBe("1.00 kg");
    expect(formatWeight(1234.5)).toBe("1.23 kg");
  });
});

describe("formatTimeOfDay", () => {
  it("renders HH:MM in 24-hour format", () => {
    expect(formatTimeOfDay("2026-05-29T10:00:00Z")).toMatch(/^\d{2}:\d{2}$/);
  });
});

describe("minutesSince", () => {
  it("returns 0 when less than a minute has elapsed", () => {
    const iso = "2026-05-29T10:00:00Z";
    const now = new Date("2026-05-29T10:00:30Z");
    expect(minutesSince(iso, now)).toBe(0);
  });

  it("returns the integer number of minutes since iso", () => {
    const iso = "2026-05-29T10:00:00Z";
    const now = new Date("2026-05-29T10:05:00Z");
    expect(minutesSince(iso, now)).toBe(5);
  });
});
