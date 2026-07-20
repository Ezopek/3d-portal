import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  cleanup();
});

import "@/locales/i18n";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders the message with no buttons when no action is given", () => {
    render(<EmptyState messageKey="catalog.empty" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });

  it("renders a single primary action button and fires its onClick", () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        messageKey="catalog.empty"
        action={{ labelKey: "catalog.actions.clear_filters", onClick }}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]!);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders primary + secondary buttons and fires each onClick (AND-too-narrow recovery)", () => {
    const onPrimary = vi.fn();
    const onSecondary = vi.fn();
    render(
      <EmptyState
        messageKey="catalog.empty"
        action={{ labelKey: "catalog.actions.switch_to_or", onClick: onPrimary }}
        secondaryAction={{ labelKey: "catalog.actions.clear_filters", onClick: onSecondary }}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
    fireEvent.click(buttons[0]!);
    fireEvent.click(buttons[1]!);
    expect(onPrimary).toHaveBeenCalledTimes(1);
    expect(onSecondary).toHaveBeenCalledTimes(1);
  });

  it("applies the destructive tone class to the message when tone='error'", () => {
    render(<EmptyState messageKey="errors.network" tone="error" />);
    const message = screen.getByText((_, el) => el?.tagName === "P");
    expect(message.className).toContain("text-destructive");
  });
});
