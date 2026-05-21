import "@/locales/i18n";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { ResetLinkDisplayModal } from "@/modules/admin/ResetLinkDisplayModal";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

const URL_VALUE = "/reset-password?token=ABC123";
const EMAIL = "victim@test.example";
const EXPIRES_AT = "2026-05-21T00:00:00Z";

describe("ResetLinkDisplayModal", () => {
  it("RM1 — renders reset_url in a read-only input", async () => {
    render(
      <ResetLinkDisplayModal
        open
        onOpenChange={() => {}}
        email={EMAIL}
        resetUrl={URL_VALUE}
        expiresAt={EXPIRES_AT}
      />,
    );

    // Codex P2 fix-up `cd6354a` (Story 8.5 close-out) made the modal render
    // an ABSOLUTE URL via `new URL(resetUrl, window.location.origin)`. The
    // relative path becomes the tail of the absolute URL, so anchor the
    // regex at `$` to match either render shape.
    const input = (await waitFor(() =>
      screen.getByDisplayValue(/\/reset-password\?token=ABC123$/),
    )) as HTMLInputElement;
    expect(input.readOnly).toBe(true);
  });

  it("RM2 — copy button invokes navigator.clipboard.writeText with reset_url", async () => {
    // Install a fresh mock clipboard *just before* render — userEvent.setup()
    // would otherwise overwrite navigator.clipboard with its own non-spy
    // implementation. fireEvent does not touch the clipboard, so the spy
    // survives the click.
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <ResetLinkDisplayModal
        open
        onOpenChange={() => {}}
        email={EMAIL}
        resetUrl={URL_VALUE}
        expiresAt={EXPIRES_AT}
      />,
    );

    // Component now resolves resetUrl against window.location.origin and
    // writes the absolute URL to the clipboard (Story 8.5 close-out
    // `cd6354a`). Build the same absolute URL here so the assertion
    // matches the component's actual clipboard payload.
    const expectedAbsolute = new URL(
      URL_VALUE,
      window.location.origin,
    ).toString();

    await waitFor(() => {
      expect(screen.getByDisplayValue(/\/reset-password\?token=ABC123$/)).toBeTruthy();
    });
    fireEvent.click(screen.getByRole("button", { name: /^Copy link$/i }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expectedAbsolute);
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Copied$/i })).toBeTruthy();
    });
  });
});
