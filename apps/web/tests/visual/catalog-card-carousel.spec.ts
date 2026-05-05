import { test } from "@playwright/test";

// Carousel was removed from ModelCard in Slice 3B (gallery-on-list deferred
// to Slice 3D when photos become first-class). Re-enable these tests once
// the carousel ships in the new ModelCard.
test.describe.skip("catalog card carousel (deferred to Slice 3D)", () => {
  test("placeholder", () => {});
});
