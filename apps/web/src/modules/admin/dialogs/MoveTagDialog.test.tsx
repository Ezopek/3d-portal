import "@/locales/i18n";

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { MoveTagDialog, type MoveTargetOption } from "@/modules/admin/dialogs/MoveTagDialog";

afterEach(cleanup);

// Fresh array identity each call — mirrors TagGroupsPage's inline `moveOptions(...)`.
function freshOptions(): MoveTargetOption[] {
  return [
    { key: "g1", label: "Material", groupId: "g1" },
    { key: "g2", label: "Style", groupId: "g2" },
    { key: "__ungrouped__", label: "Ungrouped", groupId: null },
  ];
}

function noop() {}

describe("MoveTagDialog selection stability (Story 46.2 regression)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("keeps the chosen target group across an incidental parent re-render", async () => {
    const user = userEvent.setup();
    const props = {
      open: true,
      onOpenChange: noop,
      tagName: "PLA",
      pending: false,
      errorMessage: null,
      onSubmit: vi.fn(),
    };
    const { rerender } = render(<MoveTagDialog {...props} options={freshOptions()} />);

    const select = screen.getByLabelText("Target group") as HTMLSelectElement;
    await user.selectOptions(select, "g2");
    expect(select.value).toBe("g2");

    rerender(<MoveTagDialog {...props} options={freshOptions()} />);

    // Must NOT reset to options[0] ("g1") — that would move the tag into the wrong group.
    expect((screen.getByLabelText("Target group") as HTMLSelectElement).value).toBe("g2");
  });
});
