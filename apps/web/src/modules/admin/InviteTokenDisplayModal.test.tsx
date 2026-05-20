import "@/locales/i18n";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { InviteTokenDisplayModal } from "@/modules/admin/InviteTokenDisplayModal";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

const REGISTRATION_URL = "/register?token=ABC123";
const ROLE = "member" as const;
const EXPIRES_AT = "2026-05-27T12:00:00Z";

describe("InviteTokenDisplayModal", () => {
  it("IT1 — renders registration_url as readonly input + copy button + done button", async () => {
    render(
      <InviteTokenDisplayModal
        open
        onOpenChange={() => {}}
        role={ROLE}
        registrationUrl={REGISTRATION_URL}
        expiresAt={EXPIRES_AT}
      />,
    );

    const expectedAbsolute = new URL(
      REGISTRATION_URL,
      window.location.origin,
    ).toString();

    const input = (await waitFor(() =>
      screen.getByDisplayValue(expectedAbsolute),
    )) as HTMLInputElement;
    expect(input.readOnly).toBe(true);

    expect(screen.getByRole("button", { name: /^Copy link$/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Done$/i })).toBeTruthy();
  });

  it("IT2 — clicking copy button calls navigator.clipboard.writeText with absolute URL", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <InviteTokenDisplayModal
        open
        onOpenChange={() => {}}
        role={ROLE}
        registrationUrl={REGISTRATION_URL}
        expiresAt={EXPIRES_AT}
      />,
    );

    const expectedAbsolute = new URL(
      REGISTRATION_URL,
      window.location.origin,
    ).toString();

    await waitFor(() => {
      expect(screen.getByDisplayValue(expectedAbsolute)).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /^Copy link$/i }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expectedAbsolute);
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Copied$/i })).toBeTruthy();
    });
  });

  it("IT3 — clicking done button calls onOpenChange(false)", async () => {
    const onOpenChange = vi.fn();

    render(
      <InviteTokenDisplayModal
        open
        onOpenChange={onOpenChange}
        role={ROLE}
        registrationUrl={REGISTRATION_URL}
        expiresAt={EXPIRES_AT}
      />,
    );

    const doneButton = await waitFor(() =>
      screen.getByRole("button", { name: /^Done$/i }),
    );
    fireEvent.click(doneButton);

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
