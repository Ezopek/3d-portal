import "@/locales/i18n";

import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ProfileSelectionContextView } from "@/lib/api-types";
import { ProfileSourceBadge } from "./ProfileSourceBadge";

afterEach(cleanup);

function ctx(
  source: ProfileSelectionContextView["estimate_profile_source"],
  material = "PLA",
): ProfileSelectionContextView {
  return {
    estimate_profile_source: source,
    selected_material: material,
    selected_spoolman_filament_ref:
      source === "exact_filament_mapping" ? "Bambu\x1fPLA\x1fPLA Basic" : null,
    selected_filament_name: "Bambu PLA Basic",
    orca_filament_profile_name:
      source !== "unavailable_no_profile" ? "Bambu PLA Basic @BBL X1C" : null,
  };
}

describe("ProfileSourceBadge", () => {
  it("exact_filament_mapping renders exact badge text", () => {
    render(<ProfileSourceBadge context={ctx("exact_filament_mapping")} />);
    expect(screen.getByText(/exact filament profile/i)).toBeTruthy();
  });

  it("default_material_profile renders material name in label", () => {
    render(<ProfileSourceBadge context={ctx("default_material_profile")} />);
    expect(screen.getByText(/default pla profile/i)).toBeTruthy();
  });

  it("unavailable_no_profile renders nothing", () => {
    const { container } = render(
      <ProfileSourceBadge context={ctx("unavailable_no_profile")} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("null context renders nothing (safety)", () => {
    const { container } = render(<ProfileSourceBadge context={null} />);
    expect(container.firstChild).toBeNull();
  });
});
