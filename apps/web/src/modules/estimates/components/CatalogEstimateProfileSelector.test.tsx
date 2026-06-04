import "@/locales/i18n";

import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import i18n from "@/locales/i18n";
import type { PrintIntentPresetInput } from "@/modules/estimates/lib/preset";
import { CatalogEstimateProfileSelector } from "./CatalogEstimateProfileSelector";

afterEach(() => {
  cleanup();
});

const DEFAULT_PRESET: PrintIntentPresetInput = {
  material_class: "PLA",
  quality_tier: "standard",
  spoolman_filament_ref: null,
};

describe("CatalogEstimateProfileSelector (EST-DISPLAY-1 product correction)", () => {
  it("exposes ONLY the quality profile — no material or pinned-filament controls", () => {
    render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={() => {}}
      />,
    );
    expect(screen.getByLabelText(/estimate profile/i)).toBeTruthy();
    expect(screen.queryByLabelText(/material/i)).toBeNull();
    expect(screen.queryByLabelText(/pinned filament/i)).toBeNull();
  });

  it("emits a preset that changes ONLY quality_tier, leaving material/pin at their defaults", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={(p) => calls.push(p)}
      />,
    );
    fireEvent.change(screen.getByLabelText(/estimate profile/i), {
      target: { value: "strong" },
    });
    expect(calls[0]).toEqual({ ...DEFAULT_PRESET, quality_tier: "strong" });
    // The internal defaults are preserved verbatim so the estimate query key is unchanged
    // except for the tier the member actually chose.
    expect(calls[0]?.material_class).toBe("PLA");
    expect(calls[0]?.spoolman_filament_ref).toBeNull();
  });

  it("renders backend-unavailable tiers disabled with honest copy and ignores their change events", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={(p) => calls.push(p)}
        availability={[
          { quality_tier: "aesthetic", available: false, reason: "profile_not_imported" },
          { quality_tier: "standard", available: true, reason: null },
          { quality_tier: "strong", available: false, reason: "profile_not_imported" },
        ]}
      />,
    );

    const strong = screen.getByRole("option", {
      name: /Strong.*profile not imported yet/i,
    }) as HTMLOptionElement;
    expect(strong.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(/estimate profile/i), {
      target: { value: "strong" },
    });
    expect(calls).toEqual([]);
  });

  it("fails open: an empty availability list (still loading / errored) keeps every tier selectable", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={(p) => calls.push(p)}
        availability={[]}
      />,
    );

    // Standard (the default + always-resolvable tier) must never be locked out by a transient
    // empty/errored availability response.
    expect((screen.getByRole("option", { name: "Standard" }) as HTMLOptionElement).disabled).toBe(
      false,
    );
    const strong = screen.getByRole("option", { name: "Strong" }) as HTMLOptionElement;
    expect(strong.disabled).toBe(false);
    fireEvent.change(screen.getByLabelText(/estimate profile/i), {
      target: { value: "strong" },
    });
    expect(calls.map((p) => p.quality_tier)).toEqual(["strong"]);
  });

  it("never exposes a raw Orca key in any control or option", () => {
    const { container } = render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={() => {}}
      />,
    );
    const html = container.innerHTML;
    for (const orca of [
      "filament_max_volumetric_speed",
      "layer_height",
      "nozzle_temperature",
      "bed_temp",
    ]) {
      expect(html).not.toContain(orca);
    }
  });

  it("renders the quality options in both locales", async () => {
    const { rerender } = render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("option", { name: "Standard" })).toBeTruthy();
    await i18n.changeLanguage("pl");
    rerender(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("option", { name: "Standardowa" })).toBeTruthy();
    await i18n.changeLanguage("en");
  });

  it("gives the profile control a discernible label (a11y)", () => {
    render(
      <CatalogEstimateProfileSelector
        value={DEFAULT_PRESET}
        onChange={() => {}}
      />,
    );
    expect(screen.getByLabelText(/estimate profile/i)).toBeTruthy();
  });
});
