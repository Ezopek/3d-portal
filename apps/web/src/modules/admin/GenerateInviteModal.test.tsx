import "@/locales/i18n";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { GenerateInviteModal } from "@/modules/admin/GenerateInviteModal";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

describe("GenerateInviteModal", () => {
  it("G1 — renders role select with only member + admin options (NO agent option)", async () => {
    render(
      <GenerateInviteModal open onOpenChange={() => {}} onConfirm={() => {}} />,
    );

    const roleSelect = (await waitFor(() =>
      screen.getByLabelText("Role"),
    )) as HTMLSelectElement;

    // Exactly two options, with values "member" and "admin"
    const optionValues = Array.from(roleSelect.options).map((o) => o.value);
    expect(optionValues).toEqual(["member", "admin"]);
    // Defensive negative assertion: no "agent" option at any level
    expect(screen.queryByRole("option", { name: /agent/i })).toBeNull();
    // Default selected = "member"
    expect(roleSelect.value).toBe("member");
  });

  it("G2 — renders ttl_preset select with 4 options defaulting to SEVEN_DAYS", async () => {
    render(
      <GenerateInviteModal open onOpenChange={() => {}} onConfirm={() => {}} />,
    );

    const ttlSelect = (await waitFor(() =>
      screen.getByLabelText("Validity"),
    )) as HTMLSelectElement;

    const optionValues = Array.from(ttlSelect.options).map((o) => o.value);
    expect(optionValues).toEqual([
      "ONE_DAY",
      "THREE_DAYS",
      "SEVEN_DAYS",
      "THIRTY_DAYS",
    ]);
    expect(ttlSelect.value).toBe("SEVEN_DAYS");
  });

  it("G3 — onConfirm dispatches role + ttl_preset to callback", async () => {
    const onConfirm = vi.fn();

    render(
      <GenerateInviteModal
        open
        onOpenChange={() => {}}
        onConfirm={onConfirm}
      />,
    );

    const roleSelect = (await waitFor(() =>
      screen.getByLabelText("Role"),
    )) as HTMLSelectElement;
    const ttlSelect = screen.getByLabelText("Validity") as HTMLSelectElement;

    fireEvent.change(roleSelect, { target: { value: "admin" } });
    fireEvent.change(ttlSelect, { target: { value: "ONE_DAY" } });

    fireEvent.click(screen.getByRole("button", { name: /^Generate$/ }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith({
      role: "admin",
      ttl_preset: "ONE_DAY",
    });
  });
});
