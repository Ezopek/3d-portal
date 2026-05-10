import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/locales/i18n";

import { ConfirmDialog } from "./ConfirmDialog";

afterEach(() => {
  cleanup();
});

describe("ConfirmDialog", () => {
  it("renders the title and description", () => {
    render(
      <ConfirmDialog
        open
        onOpenChange={() => undefined}
        title="Delete this thing?"
        description="This cannot be undone."
        onConfirm={() => undefined}
      />,
    );
    expect(screen.getByText(/Delete this thing/i)).toBeTruthy();
    expect(screen.getByText(/cannot be undone/i)).toBeTruthy();
  });

  it("calls onConfirm when the confirm button is clicked", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        onOpenChange={() => undefined}
        title="Title"
        confirmLabel="Yes do it"
        onConfirm={onConfirm}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /yes do it/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onOpenChange(false) on cancel and disables both buttons while pending", () => {
    const onOpenChange = vi.fn();
    render(
      <ConfirmDialog
        open
        onOpenChange={onOpenChange}
        title="Title"
        pending
        onConfirm={() => undefined}
      />,
    );
    const cancel = screen.getByRole("button", { name: /cancel|anuluj/i });
    expect(cancel.hasAttribute("disabled")).toBe(true);
    const confirm = screen.getByRole("button", { name: /confirm|potwierdź/i });
    expect(confirm.hasAttribute("disabled")).toBe(true);
  });
});
