import { test } from "@playwright/test";

// Legacy admin thumbnail flow was removed in Slice 3C. The new admin
// thumbnail picker is part of Slice 3D's PhotosTab.
test.describe.skip("admin thumbnail flow (deferred to Slice 3D)", () => {
  test("placeholder", () => {});
});
