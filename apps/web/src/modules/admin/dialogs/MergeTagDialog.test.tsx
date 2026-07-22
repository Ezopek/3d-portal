import "@/locales/i18n";

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import { MergeTagDialog, type MergeTargetOption } from "@/modules/admin/dialogs/MergeTagDialog";

afterEach(cleanup);

const BASE: MergeTargetOption[] = [
  { id: "a", label: "Alpha" },
  { id: "b", label: "Beta" },
  { id: "c", label: "Gamma" },
];

// Fresh array identity, same contents — mirrors TagGroupsPage rebuilding `options`
// via an inline `mergeOptions(...)` on every render.
function freshOptions(ids: string[] = ["a", "b", "c"]): MergeTargetOption[] {
  return BASE.filter((o) => ids.includes(o.id)).map((o) => ({ ...o }));
}

function noop() {}

describe("MergeTagDialog selection stability (Story 46.2 regression)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("keeps the chosen survivor when the parent re-renders with a new options array", async () => {
    const user = userEvent.setup();
    const props = {
      open: true,
      onOpenChange: noop,
      sourceName: "Src",
      pending: false,
      errorMessage: null,
      onSubmit: vi.fn(),
    };
    const { rerender } = render(<MergeTagDialog {...props} options={freshOptions()} />);

    const select = screen.getByLabelText("Survivor tag") as HTMLSelectElement;
    await user.selectOptions(select, "b");
    expect(select.value).toBe("b");

    // Incidental parent re-render (e.g. a window-focus refetch) → new array identity.
    rerender(<MergeTagDialog {...props} options={freshOptions()} />);

    // Must NOT snap back to options[0] ("a") — that would merge into the wrong tag.
    expect((screen.getByLabelText("Survivor tag") as HTMLSelectElement).value).toBe("b");
  });

  it("re-seeds to the first option only when the chosen survivor disappears", async () => {
    const user = userEvent.setup();
    const props = {
      open: true,
      onOpenChange: noop,
      sourceName: "Src",
      pending: false,
      errorMessage: null,
      onSubmit: vi.fn(),
    };
    const { rerender } = render(<MergeTagDialog {...props} options={freshOptions()} />);

    await user.selectOptions(screen.getByLabelText("Survivor tag"), "c");
    // "c" is removed from the candidate set (e.g. that tag was itself merged away).
    rerender(<MergeTagDialog {...props} options={freshOptions(["a", "b"])} />);

    expect((screen.getByLabelText("Survivor tag") as HTMLSelectElement).value).toBe("a");
  });
});
