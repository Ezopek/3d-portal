import { describe, it, expectTypeOf } from "vitest";

import type {
  EstimateProfileSource,
  ProfileSelectionContextView,
  EstimateView,
} from "@/lib/api-types";

// RED: these types don't exist yet — this test fails until Task 1 GREEN is done.

describe("EstimateProfileSource", () => {
  it("is a union of three literal strings", () => {
    const exact: EstimateProfileSource = "exact_filament_mapping";
    const def: EstimateProfileSource = "default_material_profile";
    const unavail: EstimateProfileSource = "unavailable_no_profile";
    expectTypeOf(exact).toMatchTypeOf<EstimateProfileSource>();
    expectTypeOf(def).toMatchTypeOf<EstimateProfileSource>();
    expectTypeOf(unavail).toMatchTypeOf<EstimateProfileSource>();
  });
});

describe("ProfileSelectionContextView", () => {
  it("has the correct shape", () => {
    expectTypeOf<ProfileSelectionContextView>().toHaveProperty(
      "estimate_profile_source",
    );
    expectTypeOf<ProfileSelectionContextView["estimate_profile_source"]>().toEqualTypeOf<EstimateProfileSource>();
    expectTypeOf<ProfileSelectionContextView["selected_material"]>().toEqualTypeOf<
      string | null
    >();
    expectTypeOf<ProfileSelectionContextView["selected_spoolman_filament_ref"]>().toEqualTypeOf<
      string | null
    >();
    expectTypeOf<ProfileSelectionContextView["selected_filament_name"]>().toEqualTypeOf<
      string | null
    >();
    expectTypeOf<ProfileSelectionContextView["orca_filament_profile_name"]>().toEqualTypeOf<
      string | null
    >();
  });
});

describe("EstimateView.profile_selection_context", () => {
  it("is nullable (ProfileSelectionContextView | null | undefined)", () => {
    expectTypeOf<EstimateView["profile_selection_context"]>().toEqualTypeOf<
      ProfileSelectionContextView | null | undefined
    >();
  });
});
