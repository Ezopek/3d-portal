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
  force_2fa_enrollment: boolean;
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
    force_2fa_enrollment: false,
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
        force_2fa_enrollment: false,
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
    // Story 12.2 — visit with `show_inactive=1` so the inactive row at index 0
    // is rendered (default state now hides it). The baseline therefore captures
    // both the active rows and the muted-row styling on the inactive row.
    await page.goto("/admin/users?page_size=25&show_inactive=1");
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

    // FR5-ADMIN-4 — no bulk-select column inside the data table. The Story
    // 12.2 page-level "Show inactive accounts" filter checkbox is a single
    // global control outside the table and is intentionally not constrained
    // by this guard.
    expect(await page.locator('table input[type="checkbox"]').count()).toBe(0);
    expect(await page.locator('thead input[type="checkbox"]').count()).toBe(0);
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

test.describe("/admin/users — AdminTabs active-state regression guard (Story 12.1)", () => {
  test("Invites tab is an enabled link routing to /admin/invites (Story 12.1 unblock)", async ({
    page,
  }) => {
    await stubAdminUsersPage(page);
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const invitesTab = page.getByRole("tab", { name: /Invites|Zaproszenia/i });
    // Story 12.1 flipped AdminTabs.tsx <span aria-disabled> → <Link to="/admin/invites">.
    // Expect: rendered as <a> with href, no aria-disabled attribute, not aria-selected
    // (user is on /admin/users, not /admin/invites).
    await expect(invitesTab).not.toHaveAttribute("aria-disabled", "true");
    await expect(invitesTab).toHaveAttribute("href", "/admin/invites");
    await expect(invitesTab).toHaveAttribute("aria-selected", "false");
  });
});

// The dev server detects `pl-PL` locale (playwright.config.ts) so the page
// renders in Polish; aria labels and menu text below match pl.json verbatim.
test.describe("/admin/users — Story 8.3 per-row actions surface", () => {
  test("kebab menu opens and shows the four actions on a member row", async ({
    page,
  }) => {
    const member = rowFixture(7, {
      id: "00000000-0000-0000-0000-000000000007",
    });
    await stubAdminUsersPage(page, {
      total: 1,
      items: [member],
      page: 1,
      page_size: 50,
    });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const kebab = page.getByRole("button", {
      name: /Akcje dla member7@test\.example/i,
    });
    await expect(kebab).toBeEnabled();
    // ``force: true`` because narrow viewports (Pixel 5 in mobile-*) let the
    // sticky table header overlap the kebab; the menu wiring itself is what
    // we exercise here, layout regressions are caught by the baseline PNGs.
    await kebab.click({ force: true });

    await expect(page.getByText("Zmień rolę").first()).toBeVisible();
    await expect(page.getByText("Dezaktywuj")).toBeVisible();
    await expect(
      page.getByText("Wymuś wylogowanie ze wszystkich sesji"),
    ).toBeVisible();
    await expect(page.getByText("Reaktywuj")).toHaveCount(0);
  });

  test("Story 8.4 — kebab shows force-disable item for active totp-enabled non-flagged member", async ({
    page,
  }) => {
    const member = rowFixture(81, {
      id: "00000000-0000-0000-0000-000000000081",
      totp_enabled: true,
      force_2fa_enrollment: false,
    });
    await stubAdminUsersPage(page, {
      total: 1,
      items: [member],
      page: 1,
      page_size: 50,
    });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const kebab = page.getByRole("button", {
      name: /Akcje dla member81@test\.example/i,
    });
    await kebab.click({ force: true });

    // Force-disable 2FA is visible (totp_enabled=true).
    await expect(
      page.getByText(/Wymuś wyłączenie 2FA/i).first(),
    ).toBeVisible();
    // Force 2FA enrollment is NOT visible (already enrolled).
    await expect(page.getByText(/Wymuś włączenie 2FA/i)).toHaveCount(0);
    // Story 8.3 items still present.
    await expect(page.getByText("Zmień rolę").first()).toBeVisible();
    await expect(page.getByText("Dezaktywuj")).toBeVisible();
    await expect(
      page.getByText("Wymuś wylogowanie ze wszystkich sesji"),
    ).toBeVisible();
  });

  test("Story 8.4 — kebab shows force-enroll item for active non-enrolled non-flagged member", async ({
    page,
  }) => {
    const member = rowFixture(91, {
      id: "00000000-0000-0000-0000-000000000091",
      totp_enabled: false,
      force_2fa_enrollment: false,
    });
    await stubAdminUsersPage(page, {
      total: 1,
      items: [member],
      page: 1,
      page_size: 50,
    });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const kebab = page.getByRole("button", {
      name: /Akcje dla member91@test\.example/i,
    });
    await kebab.click({ force: true });

    // Force 2FA enrollment is visible (not enrolled + not flagged).
    await expect(
      page.getByText(/Wymuś włączenie 2FA/i).first(),
    ).toBeVisible();
    // Force-disable 2FA is NOT visible (not enrolled).
    await expect(page.getByText(/Wymuś wyłączenie 2FA/i)).toHaveCount(0);
    // Story 8.3 items still present.
    await expect(page.getByText("Zmień rolę").first()).toBeVisible();
  });

  test("kebab disabled on self and agent rows; enabled on member row", async ({
    page,
  }) => {
    const member = rowFixture(11, {
      id: "00000000-0000-0000-0000-000000000011",
    });
    const agent = rowFixture(12, {
      id: "00000000-0000-0000-0000-000000000012",
      email: "agent@portal.local",
      role: "agent",
    });
    const own: AdminUserFixture = {
      id: "u1",
      email: "admin@localhost.localdomain",
      display_name: "Admin",
      role: "admin",
      created_at: "2026-05-19T08:00:00Z",
      last_active_at: "2026-05-20T07:00:00Z",
      totp_enabled: false,
      is_active: true,
      force_2fa_enrollment: false,
    };
    await stubAdminUsersPage(page, {
      total: 3,
      items: [own, agent, member],
      page: 1,
      page_size: 50,
    });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const memberKebab = page.getByRole("button", {
      name: /Akcje dla member11@test\.example/i,
    });
    await expect(memberKebab).toBeEnabled();

    const agentKebab = page.getByRole("button", {
      name: /Akcje dla agent@portal\.local/i,
    });
    await expect(agentKebab).toHaveAttribute("aria-disabled", "true");

    const ownKebab = page.getByRole("button", {
      name: /Akcje dla admin@localhost\.localdomain/i,
    });
    await expect(ownKebab).toHaveAttribute("aria-disabled", "true");
  });

  test("Story 8.5 — kebab shows 'Issue password reset link' item for active non-flagged member (Test 10, DOM-assert)", async ({
    page,
  }) => {
    const member = rowFixture(101, {
      id: "00000000-0000-0000-0000-000000000101",
      totp_enabled: false,
      force_2fa_enrollment: false,
    });
    await stubAdminUsersPage(page, {
      total: 1,
      items: [member],
      page: 1,
      page_size: 50,
    });
    await page.goto("/admin/users");
    await page.getByRole("heading", { level: 1 }).waitFor({ state: "visible" });
    await waitForReady(page);

    const kebab = page.getByRole("button", {
      name: /Akcje dla member101@test\.example/i,
    });
    await kebab.click({ force: true });

    await expect(
      page.getByText(/Wystaw link do resetu hasła/i).first(),
    ).toBeVisible();
    // Story 8.3 + 8.4 items still present.
    await expect(page.getByText("Zmień rolę").first()).toBeVisible();
    await expect(page.getByText(/Wymuś włączenie 2FA/i).first()).toBeVisible();
  });
});
