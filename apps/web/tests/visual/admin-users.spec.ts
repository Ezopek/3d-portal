import { expect, test } from "./_test";

import { waitForReady } from "./helpers";
import type { Page, Route } from "@playwright/test";

interface AdminUserFixture {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "agent" | "member";
  created_at: string;
  last_active_at: string | null;
  totp_enabled: boolean;
  is_active: boolean;
}

interface UsersListFixture {
  total: number;
  items: AdminUserFixture[];
  page: number;
  page_size: number;
}

function rowFixture(i: number, overrides: Partial<AdminUserFixture> = {}): AdminUserFixture {
  return {
    id: `00000000-0000-0000-0000-${String(i).padStart(12, "0")}`,
    email: `member${i}@test.example`,
    display_name: `Member ${i}`,
    role: "member",
    created_at: "2026-05-19T08:00:00Z",
    last_active_at: "2026-05-20T07:00:00Z",
    totp_enabled: false,
    is_active: true,
    ...overrides,
  };
}

async function stubAdminUsersPage(page: Page, payload?: UsersListFixture) {
  await page.route("**/api/auth/me", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u1",
        email: "admin@localhost.localdomain",
        display_name: "Admin",
        role: "admin",
      }),
    }),
  );

  const body: UsersListFixture = payload ?? {
    total: 1,
    items: [
      {
        id: "u1",
        email: "admin@localhost.localdomain",
        display_name: "Admin",
        role: "admin",
        created_at: "2026-05-19T08:00:00Z",
        last_active_at: "2026-05-20T07:00:00Z",
        totp_enabled: false,
        is_active: true,
      },
    ],
    page: 1,
    page_size: 50,
  };

  await page.route("**/api/admin/users**", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    }),
  );
}

test.describe("/admin/users baselines", () => {
  test("empty state matches baseline", async ({ page }) => {
    await stubAdminUsersPage(page, { total: 0, items: [], page: 1, page_size: 50 });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("admin-users-empty.png", {
      fullPage: true,
    });
  });

  test("one-row state matches baseline", async ({ page }) => {
    await stubAdminUsersPage(page);
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("admin-users-one-row.png", {
      fullPage: true,
    });
  });

  test("many-rows state matches baseline", async ({ page }) => {
    const items: AdminUserFixture[] = Array.from({ length: 25 }, (_, i) => {
      const overrides: Partial<AdminUserFixture> = {};
      if (i === 0) overrides.is_active = false;
      if (i === 1) overrides.totp_enabled = true;
      if (i === 2) overrides.last_active_at = null;
      return rowFixture(i, overrides);
    });
    await stubAdminUsersPage(page, {
      total: 137,
      items,
      page: 1,
      page_size: 25,
    });
    await page.goto("/admin/users?page_size=25");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);
    await expect(page).toHaveScreenshot("admin-users-many-rows.png", {
      fullPage: true,
    });
  });
});

test.describe("/admin/users — FR5-ADMIN-4 negative AC enforcement", () => {
  test("no bulk-select controls anywhere in the page", async ({ page }) => {
    const items: AdminUserFixture[] = Array.from({ length: 10 }, (_, i) => rowFixture(i));
    await stubAdminUsersPage(page, {
      total: 10,
      items,
      page: 1,
      page_size: 50,
    });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    expect(await page.locator('table input[type="checkbox"]').count()).toBe(0);
    expect(await page.locator('thead input[type="checkbox"]').count()).toBe(0);
    expect(await page.locator('input[type="checkbox"]').count()).toBe(0);
    expect(
      await page.getByRole("button", { name: /bulk/i }).count(),
    ).toBe(0);
    expect(
      await page
        .getByRole("button", { name: /wszystkie|zaznacz wszyst/i })
        .count(),
    ).toBe(0);
    expect(
      await page.getByRole("menuitem", { name: /bulk|zbiorow/i }).count(),
    ).toBe(0);
  });
});

test.describe("/admin/users — AdminTabs disabled-state regression guard", () => {
  test("Invites tab stays aria-disabled until Story 8.6", async ({ page }) => {
    await stubAdminUsersPage(page);
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const invitesTab = page.getByRole("tab", { name: /Invites|Zaproszenia/i });
    await expect(invitesTab).toHaveAttribute("aria-disabled", "true");
  });
});
