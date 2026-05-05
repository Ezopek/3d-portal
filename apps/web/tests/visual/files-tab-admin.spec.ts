import { test } from "@playwright/test";

// Legacy admin file selection (render-selection checkboxes) was removed
// in Slice 3C. The new admin file-management UX lands in Slice 3E.
test.describe.skip("files tab admin (deferred to Slice 3E)", () => {
  test("placeholder", () => {});
});
