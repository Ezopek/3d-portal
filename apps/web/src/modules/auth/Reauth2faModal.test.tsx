import "@/locales/i18n";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { Reauth2faModal } from "./Reauth2faModal";

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

afterEach(() => {
  cleanup();
});

function defaultProps(overrides: Partial<Parameters<typeof Reauth2faModal>[0]> = {}) {
  return {
    title: "Regenerate recovery codes",
    submitLabel: "Generate new codes",
    pending: false,
    error: null,
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  };
}

describe("Reauth2faModal (Story 7.5)", () => {
  it("R1 — Submit button is disabled when password is empty OR code length != 6; enabled when both fields valid", () => {
    const props = defaultProps();
    render(<Reauth2faModal {...props} />);
    const submit = screen.getByRole("button", {
      name: /generate new codes/i,
    }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);

    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const codeInput = screen.getByLabelText(/6-digit/i) as HTMLInputElement;

    fireEvent.change(passwordInput, { target: { value: "pw" } });
    expect(submit.disabled).toBe(true);

    fireEvent.change(codeInput, { target: { value: "12345" } });
    expect(submit.disabled).toBe(true);

    fireEvent.change(codeInput, { target: { value: "123456" } });
    expect(submit.disabled).toBe(false);

    fireEvent.change(passwordInput, { target: { value: "" } });
    expect(submit.disabled).toBe(true);
  });

  it("R2 — onSubmit is called with (password, totp_code) on form submit; not called when fields invalid", () => {
    const onSubmit = vi.fn();
    render(<Reauth2faModal {...defaultProps({ onSubmit })} />);
    const submit = screen.getByRole("button", { name: /generate new codes/i });
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const codeInput = screen.getByLabelText(/6-digit/i) as HTMLInputElement;

    // Fields invalid -> click is a no-op.
    fireEvent.click(submit);
    expect(onSubmit).not.toHaveBeenCalled();

    // Both valid -> submit fires with the values.
    fireEvent.change(passwordInput, { target: { value: "Sup3rPassword!" } });
    fireEvent.change(codeInput, { target: { value: "123456" } });
    fireEvent.click(submit);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("Sup3rPassword!", "123456");
  });

  it("R3 — Submit button + inputs are disabled while pending=true; cancel button still enabled and triggers onCancel", () => {
    const onCancel = vi.fn();
    render(<Reauth2faModal {...defaultProps({ pending: true, onCancel })} />);
    const submit = screen.getByRole("button", {
      name: /generate new codes/i,
    }) as HTMLButtonElement;
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;
    const codeInput = screen.getByLabelText(/6-digit/i) as HTMLInputElement;
    const cancel = screen.getByRole("button", { name: /cancel/i }) as HTMLButtonElement;

    expect(submit.disabled).toBe(true);
    expect(passwordInput.disabled).toBe(true);
    expect(codeInput.disabled).toBe(true);
    // Cancel must remain enabled so the user can abort a stuck request.
    expect(cancel.disabled).toBe(false);
    fireEvent.click(cancel);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
