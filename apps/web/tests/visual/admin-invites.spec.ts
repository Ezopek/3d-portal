import { expect, test } from "./_test";

import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

interface AdminInviteFixture {
  invite_id: string;
  role: "admin" | "member";
  ttl_seconds: number;
  generated_by_user_id: string | null;
  generated_at: string;
  expires_at: string;
  used_by_user_id: string | null;
  used_at: string | null;
  used_from_ip: string | null;
  revoked_at: string | null;
  status: "active" | "used" | "expired" | "revoked";
}

interface InvitesListFixture {
  total: number;
  items: AdminInviteFixture[];
  page: number;
  page_size: number;
}

function inviteFixture(
  i: number,
  overrides: Partial<AdminInviteFixture> = {},
): AdminInviteFixture {
  return {
    invite_id: `00000000-0000-0000-0000-${String(i).padStart(12, "0")}`,
    role: "member",
    ttl_seconds: 7 * 24 * 60 * 60,
    generated_by_user_id: "00000000-0000-0000-0000-000000000001",
    generated_at: "2026-05-19T08:00:00Z",
    expires_at: "2026-05-26T08:00:00Z",
    used_by_user_id: null,
    used_at: null,
    used_from_ip: null,
    revoked_at: null,
    status: "active",
    ...overrides,
  };
}

async function stubAdminInvitesPage(
  page: Page,
  payload?: InvitesListFixture,
) {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000001",
        email: "admin@localhost.localdomain",
        display_name: "Admin",
        role: "admin",
      }),
    }),
  );

  const body: InvitesListFixture = payload ?? {
    total: 0,
    items: [],
    page: 1,
    page_size: 50,
  };

  await page.route("**/api/admin/invites**", (route: Route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    }
    // POST generate / POST {id}/revoke are not exercised by the baselines
    // — they need separate routes if a future test demands them.
    return route.fulfill({ status: 204, body: "" });
  });
}

test.describe("/admin/invites baselines", () => {
  test("empty state matches baseline", async ({ page }) => {
    await stubAdminInvitesPage(page);
    await page.goto("/admin/invites");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("admin-invites-empty.png", {
      fullPage: true,
    });
  });

  test("mixed-status state matches baseline", async ({ page }) => {
    await stubAdminInvitesPage(page, {
      total: 4,
      page: 1,
      page_size: 50,
      items: [
        inviteFixture(1, { status: "active" }),
        inviteFixture(2, {
          status: "used",
          used_by_user_id: "00000000-0000-0000-0000-000000000099",
          used_at: "2026-05-20T11:00:00Z",
          used_from_ip: "10.0.0.42",
        }),
        inviteFixture(3, {
          status: "expired",
          expires_at: "2026-05-10T00:00:00Z",
        }),
        inviteFixture(4, {
          status: "revoked",
          revoked_at: "2026-05-18T09:00:00Z",
        }),
      ],
    });
    await page.goto("/admin/invites");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("admin-invites-mixed-status.png", {
      fullPage: true,
    });
  });

  test("generate-modal-open state matches baseline", async ({ page }) => {
    await stubAdminInvitesPage(page);
    await page.goto("/admin/invites");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    await page
      .getByRole("button", { name: /Generate invite|Wystaw zaproszenie/i })
      .click();
    await page
      .getByRole("dialog")
      .filter({ hasText: /Generate new invite|Wystaw nowe zaproszenie/i })
      .waitFor({ state: "visible" });
    await waitForReady(page);

    await expect(page).toHaveScreenshot(
      "admin-invites-generate-modal-open.png",
      {
        fullPage: true,
      },
    );
  });

  test("revoke-confirm state matches baseline", async ({ page }) => {
    await stubAdminInvitesPage(page, {
      total: 1,
      page: 1,
      page_size: 50,
      items: [inviteFixture(1, { status: "active" })],
    });
    await page.goto("/admin/invites");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    // Sticky admin header overlaps the Revoke button on mobile viewports;
    // scroll to top + use force-click to bypass the pointer-events intercept.
    const revokeBtn = page.getByRole("button", {
      name: /^Revoke$|^Odwołaj$/i,
    });
    await revokeBtn.scrollIntoViewIfNeeded();
    await revokeBtn.click({ force: true });
    await page
      .getByRole("dialog")
      .filter({
        hasText: /Revoke invite for|Odwołać zaproszenie dla/i,
      })
      .waitFor({ state: "visible" });
    await waitForReady(page);

    await expect(page).toHaveScreenshot("admin-invites-revoke-confirm.png", {
      fullPage: true,
    });
  });
});
