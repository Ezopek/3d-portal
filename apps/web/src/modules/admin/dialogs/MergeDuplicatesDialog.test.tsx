import "@/locales/i18n";

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import {
  MergeDuplicatesDialog,
  type MergeDuplicatesCandidate,
} from "@/modules/admin/dialogs/MergeDuplicatesDialog";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function candidate(overrides: Partial<MergeDuplicatesCandidate> & { id: string }): MergeDuplicatesCandidate {
  return {
    label: overrides.id,
    name_en: overrides.id,
    model_count: 0,
    ...overrides,
  };
}

function baseProps(candidates: MergeDuplicatesCandidate[]) {
  return {
    open: true,
    onOpenChange: vi.fn(),
    candidates,
    pending: false,
    errorMessage: null,
    onSubmit: vi.fn(),
  };
}

describe("MergeDuplicatesDialog (Story 46.3)", () => {
  beforeEach(() => {
    void i18n.changeLanguage("en");
  });

  it("defaults the survivor to the highest model_count candidate", async () => {
    const candidates = [
      candidate({ id: "a", label: "Bracket", name_en: "Bracket", model_count: 2 }),
      candidate({ id: "b", label: "Brackets", name_en: "Brackets", model_count: 12 }),
      candidate({ id: "c", label: "bracket", name_en: "bracket", model_count: 5 }),
    ];
    render(<MergeDuplicatesDialog {...baseProps(candidates)} />);

    expect(await screen.findByRole("radio", { name: "Brackets" })).toHaveProperty("checked", true);
    expect(screen.getByRole("radio", { name: "Bracket" })).toHaveProperty("checked", false);
    expect(screen.getByRole("radio", { name: "bracket" })).toHaveProperty("checked", false);
  });

  it("tie-breaks equal model_count alphabetically by normalized name_en", async () => {
    const candidates = [
      candidate({ id: "z", label: "Zeta", name_en: "Zeta", model_count: 4 }),
      candidate({ id: "a", label: "Alpha", name_en: "Alpha", model_count: 4 }),
    ];
    render(<MergeDuplicatesDialog {...baseProps(candidates)} />);

    expect(await screen.findByRole("radio", { name: "Alpha" })).toHaveProperty("checked", true);
    expect(screen.getByRole("radio", { name: "Zeta" })).toHaveProperty("checked", false);
  });

  it("re-derives options live when candidates shrink while open, resetting selection only if it disappeared", async () => {
    const candidates = [
      candidate({ id: "a", label: "Bracket", name_en: "Bracket", model_count: 2 }),
      candidate({ id: "b", label: "Brackets", name_en: "Brackets", model_count: 12 }),
      candidate({ id: "c", label: "bracket", name_en: "bracket", model_count: 5 }),
    ];
    const props = baseProps(candidates);
    const { rerender } = render(<MergeDuplicatesDialog {...props} />);

    const user = userEvent.setup();
    // Admin overrides the default to the lowest-count candidate.
    await user.click(await screen.findByRole("radio", { name: "Bracket" }));
    expect(screen.getByRole("radio", { name: "Bracket" })).toHaveProperty("checked", true);

    // Candidate "b" (the previously-default survivor) merges away concurrently;
    // the admin's override ("a") is still present, so it must be preserved.
    rerender(<MergeDuplicatesDialog {...props} candidates={[candidates[0]!, candidates[2]!]} />);
    expect(screen.getByRole("radio", { name: "Bracket" })).toHaveProperty("checked", true);
    expect(screen.queryByRole("radio", { name: "Brackets" })).toBeNull();

    // Now the admin's own selection ("a") disappears too — re-seed to the new
    // highest model_count among what remains ("c", count 5).
    rerender(<MergeDuplicatesDialog {...props} candidates={[candidates[2]!]} />);
    expect(screen.getByRole("radio", { name: "bracket" })).toHaveProperty("checked", true);
  });

  it("disables submit when fewer than 2 candidates remain", async () => {
    const candidates = [candidate({ id: "a", label: "Bracket", model_count: 2 })];
    render(<MergeDuplicatesDialog {...baseProps(candidates)} />);

    const submit = await screen.findByRole("button", { name: "Confirm merge" });
    expect((submit as HTMLButtonElement).disabled).toBe(true);
  });

  it("enables submit and calls onSubmit with the selected survivor id", async () => {
    const candidates = [
      candidate({ id: "a", label: "Bracket", model_count: 2 }),
      candidate({ id: "b", label: "Brackets", model_count: 12 }),
    ];
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<MergeDuplicatesDialog {...baseProps(candidates)} onSubmit={onSubmit} />);

    const submit = await screen.findByRole("button", { name: "Confirm merge" });
    expect((submit as HTMLButtonElement).disabled).toBe(false);
    await user.click(submit);

    expect(onSubmit).toHaveBeenCalledWith("b");
  });

  // Review finding (dev-repair): the most common real duplicate is a tag typed
  // twice with the EXACT same text — without a disambiguator, both radios get
  // the same accessible name, making the choice unreachable via screen reader.
  it("disambiguates the accessible name when two candidates share the exact same label", async () => {
    const candidates = [
      candidate({ id: "a", label: "Bracket", name_en: "Bracket", model_count: 0 }),
      candidate({ id: "b", label: "Bracket", name_en: "Bracket", model_count: 0 }),
    ];
    render(<MergeDuplicatesDialog {...baseProps(candidates)} />);

    expect(await screen.findByRole("radio", { name: "Bracket (1)" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Bracket (2)" })).toBeTruthy();
  });

  it("keeps the plain label as the accessible name when no collision exists", async () => {
    const candidates = [
      candidate({ id: "a", label: "Bracket", name_en: "Bracket", model_count: 2 }),
      candidate({ id: "b", label: "Brackets", name_en: "Brackets", model_count: 12 }),
    ];
    render(<MergeDuplicatesDialog {...baseProps(candidates)} />);

    expect(await screen.findByRole("radio", { name: "Bracket" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Brackets" })).toBeTruthy();
  });
});
