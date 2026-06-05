import "@/locales/i18n";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import i18n from "@/locales/i18n";
import type { PrintIntentPresetInput } from "@/modules/estimates/lib/preset";
import { CatalogEstimateProfileSelector } from "./CatalogEstimateProfileSelector";

afterEach(cleanup);

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

const PLA_STANDARD: PrintIntentPresetInput = {
  material_class: "PLA",
  quality_tier: "standard",
  spoolman_filament_ref: null,
};

const TPU_STANDARD: PrintIntentPresetInput = {
  material_class: "TPU",
  quality_tier: "standard",
  spoolman_filament_ref: null,
};

function qualitySelect() {
  return screen.getByLabelText(/quality/i) as HTMLSelectElement;
}

function tierOption(name: RegExp) {
  return screen.getByRole("option", { name }) as HTMLOptionElement;
}

describe("CatalogEstimateProfileSelector (Story 33.1 — Path B material reversal; E33.1 quality-select correction)", () => {
  it("surfaces a MATERIAL control (the documented EST-DISPLAY-1 reversal)", () => {
    render(
      <CatalogEstimateProfileSelector value={PLA_STANDARD} onChange={() => {}} />,
    );
    expect(screen.getByLabelText(/material/i)).toBeTruthy();
  });

  it("renders the quality control as a native select (E33.1 correction — not a radio group)", () => {
    render(
      <CatalogEstimateProfileSelector value={PLA_STANDARD} onChange={() => {}} />,
    );
    expect(qualitySelect().tagName).toBe("SELECT");
    // The old pill/radio group is gone — no radio semantics on this surface.
    expect(screen.queryByRole("radiogroup")).toBeNull();
    expect(screen.queryByRole("radio")).toBeNull();
  });

  it("changing material to TPU resets the tier to a compatible one and keeps the spool pin null (AC-18)", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={PLA_STANDARD}
        onChange={(p) => calls.push(p)}
      />,
    );
    fireEvent.change(screen.getByLabelText(/material/i), {
      target: { value: "TPU" },
    });
    // Q5 operator decision: TPU is currently standard-only, so a PLA/standard preset stays
    // on standard while switching material; the spool pin STAYS null (preserved invariant).
    expect(calls[0]?.material_class).toBe("TPU");
    expect(calls[0]?.quality_tier).toBe("standard");
    expect(calls[0]?.spoolman_filament_ref).toBeNull();
  });

  it("HIDES structurally-incompatible tiers for the chosen material (AC-19)", () => {
    render(
      <CatalogEstimateProfileSelector value={TPU_STANDARD} onChange={() => {}} />,
    );
    // Q5 operator decision: TPU offers only Standard; Aesthetic/Strong are not rendered as options.
    expect(screen.getByRole("option", { name: /Standard/i })).toBeTruthy();
    expect(screen.queryByRole("option", { name: /Aesthetic/i })).toBeNull();
    expect(screen.queryByRole("option", { name: /Strong/i })).toBeNull();
  });

  it("DISABLES compatible-but-unavailable tiers with an explanation and ignores selection (AC-19)", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={PLA_STANDARD}
        onChange={(p) => calls.push(p)}
        availability={[
          { quality_tier: "aesthetic", available: false, reason: "profile_not_imported" },
          { quality_tier: "standard", available: true, reason: null },
          { quality_tier: "strong", available: false, reason: "profile_not_imported" },
        ]}
      />,
    );
    const strong = tierOption(/Strong.*Not available yet/i);
    expect(strong.disabled).toBe(true);
    // The selectTier guard ignores an unavailable tier even if a change event reaches it.
    fireEvent.change(qualitySelect(), { target: { value: "strong" } });
    expect(calls).toEqual([]);
  });

  it("fails OPEN: empty availability keeps every compatible tier selectable, Standard never locked out (AC-20)", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={PLA_STANDARD}
        onChange={(p) => calls.push(p)}
        availability={[]}
      />,
    );
    expect(tierOption(/^Standard$/).disabled).toBe(false);
    const strong = tierOption(/^Strong$/);
    expect(strong.disabled).toBe(false);
    fireEvent.change(qualitySelect(), { target: { value: "strong" } });
    expect(calls.map((p) => p.quality_tier)).toEqual(["strong"]);
  });

  it("a tier change keeps spoolman_filament_ref null even if the caller carried a ref (invariant #3)", () => {
    const calls: PrintIntentPresetInput[] = [];
    render(
      <CatalogEstimateProfileSelector
        value={{ ...PLA_STANDARD, spoolman_filament_ref: "stale-ref" }}
        onChange={(p) => calls.push(p)}
      />,
    );
    fireEvent.change(qualitySelect(), { target: { value: "strong" } });
    expect(calls[0]?.quality_tier).toBe("strong");
    expect(calls[0]?.spoolman_filament_ref).toBeNull();
  });

  it("self-defends: an incompatible incoming quality_tier displays the first compatible tier, no desync", () => {
    render(
      <CatalogEstimateProfileSelector
        value={{ ...TPU_STANDARD, quality_tier: "strong" }}
        onChange={() => {}}
      />,
    );
    // TPU offers only Standard; "strong" is incompatible so no <option> for it exists. The
    // controlled select must show Standard rather than silently falling back to a wrong option.
    expect(qualitySelect().value).toBe("standard");
    expect(screen.queryByRole("option", { name: /Strong/i })).toBeNull();
  });

  it("never exposes a raw Orca key or a Spoolman pin control (AC-18)", () => {
    const { container } = render(
      <CatalogEstimateProfileSelector value={PLA_STANDARD} onChange={() => {}} />,
    );
    const html = container.innerHTML;
    for (const orca of [
      "filament_max_volumetric_speed",
      "layer_height",
      "nozzle_temperature",
      "spoolman_filament_ref",
    ]) {
      expect(html).not.toContain(orca);
    }
    // No spool/filament pin control is introduced on this surface.
    expect(screen.queryByLabelText(/pinned filament|spool/i)).toBeNull();
  });

  it("renders material + tier controls in both locales", async () => {
    const { rerender } = render(
      <CatalogEstimateProfileSelector value={PLA_STANDARD} onChange={() => {}} />,
    );
    expect(screen.getByRole("option", { name: "Standard" })).toBeTruthy();
    await i18n.changeLanguage("pl");
    rerender(
      <CatalogEstimateProfileSelector value={PLA_STANDARD} onChange={() => {}} />,
    );
    expect(screen.getByRole("option", { name: "Standardowa" })).toBeTruthy();
    await i18n.changeLanguage("en");
  });
});
