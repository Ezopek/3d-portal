import "@/locales/i18n";

import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { OverrideContextView } from "@/lib/api-types";
import { OverrideContextPanel } from "./OverrideContextPanel";

afterEach(cleanup);

function ctx(
  overrides: Partial<OverrideContextView> = {},
): OverrideContextView {
  return {
    material_class: "PETG",
    quality_tier: "strong",
    pinned_filament_name: null,
    custom_overrides_applied: false,
    purchase_url: null,
    ...overrides,
  };
}

describe("OverrideContextPanel (AC-5)", () => {
  it("shows the material class verbatim and the pinned filament name", () => {
    render(
      <OverrideContextPanel
        context={ctx({ pinned_filament_name: "PLA Speed Matt White" })}
      />,
    );
    expect(screen.getByText("PETG")).toBeTruthy(); // untranslated material class
    expect(screen.getByText("PLA Speed Matt White")).toBeTruthy();
  });

  it("shows a 'custom profile applied' badge when overrides are present", () => {
    render(
      <OverrideContextPanel
        context={ctx({
          pinned_filament_name: "X",
          custom_overrides_applied: true,
        })}
      />,
    );
    expect(screen.getByText(/custom filament profile applied/i)).toBeTruthy();
  });

  it("never renders override values / g-code / settings_ids for a pinned filament", () => {
    // The DTO does not even carry these; assert none surface in the DOM regardless.
    const { container } = render(
      <OverrideContextPanel
        context={ctx({
          pinned_filament_name: "PLA Speed Matt White",
          custom_overrides_applied: true,
          purchase_url: "https://shop.example.com/pla-white",
        })}
      />,
    );
    const text = container.textContent ?? "";
    for (const leak of [
      "8.0",
      "215",
      "1.24",
      "filament_max_volumetric_speed",
      "nozzle_temperature",
      "filament_density",
      "settings_ids",
      "gcode",
    ]) {
      expect(text).not.toContain(leak);
    }
  });

  it("renders the purchase link as a safe external anchor", () => {
    render(
      <OverrideContextPanel
        context={ctx({
          pinned_filament_name: "X",
          purchase_url: "https://shop.example.com/pla-white",
        })}
      />,
    );
    const link = screen.getByRole("link", {
      name: /purchase link/i,
    }) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe(
      "https://shop.example.com/pla-white",
    );
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("shows the material-default context (no badge, no link) when nothing is pinned", () => {
    render(<OverrideContextPanel context={ctx()} />);
    expect(screen.queryByText(/custom filament profile applied/i)).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
  });
});
