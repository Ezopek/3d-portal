import { test } from "@playwright/test";

// Admin actions on catalog detail (thumbnail picker, render selection,
// share button) were removed in Slice 3C and return in Slice 3E with
// the new edit-pattern. Re-enable when 3E ships.
test.describe.skip("catalog detail admin (deferred to Slice 3E)", () => {
  test("placeholder", () => {});
});
