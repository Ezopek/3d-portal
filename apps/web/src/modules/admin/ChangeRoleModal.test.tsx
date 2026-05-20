import "@/locales/i18n";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import type { AdminUser } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { ChangeRoleModal } from "@/modules/admin/ChangeRoleModal";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

function memberTarget(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    id: "00000000-0000-0000-0000-000000000100",
    email: "victim@test.example",
    display_name: "Victim",
    role: "member",
    created_at: "2026-05-19T00:00:00Z",
    last_active_at: null,
    totp_enabled: false,
    is_active: true,
    ...overrides,
  };
}

describe("ChangeRoleModal", () => {
  it("R1 — renders role select with current target role pre-selected", async () => {
    render(
      <ChangeRoleModal
        open
        onOpenChange={() => {}}
        target={memberTarget()}
        onConfirm={() => {}}
      />,
    );

    const select = (await waitFor(() =>
      screen.getByRole("combobox", { name: /change role/i }),
    )) as HTMLSelectElement;
    expect(select.value).toBe("member");
  });

  it("R2 — agent option is disabled in the select", async () => {
    render(
      <ChangeRoleModal
        open
        onOpenChange={() => {}}
        target={memberTarget()}
        onConfirm={() => {}}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("combobox", { name: /change role/i }),
      ).toBeTruthy();
    });
    const agentOption = screen.getByRole("option", {
      name: /Agent \(system-managed\)/i,
    }) as HTMLOptionElement;
    expect(agentOption.disabled).toBe(true);
  });

  it("R3 — confirm button calls onConfirm with selected role", async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    render(
      <ChangeRoleModal
        open
        onOpenChange={() => {}}
        target={memberTarget()}
        onConfirm={onConfirm}
      />,
    );

    const select = (await waitFor(() =>
      screen.getByRole("combobox", { name: /change role/i }),
    )) as HTMLSelectElement;
    await user.selectOptions(select, "admin");

    await user.click(screen.getByRole("button", { name: /^Confirm$/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith("admin");
  });
});
