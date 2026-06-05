import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { AdminProfileSlot, AdminProfileStatus } from "@/lib/api-types";
import i18n from "@/locales/i18n";
import { ProfileInventoryGrid } from "@/modules/admin/ProfileInventoryGrid";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
});

beforeAll(async () => {
  await i18n.changeLanguage("en");
});

const PRINTER_REF = "creality-k1-max-microswiss-hf";

function renderGrid(slots: AdminProfileSlot[]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return render(<ProfileInventoryGrid slots={slots} printerRef={PRINTER_REF} />, {
    wrapper: Wrapper,
  });
}

function slot(
  material: AdminProfileSlot["material_class"],
  tier: AdminProfileSlot["quality_tier"],
  status: AdminProfileStatus,
  overrides: Partial<AdminProfileSlot> = {},
): AdminProfileSlot {
  const base: AdminProfileSlot = {
    material_class: material,
    quality_tier: tier,
    imported: status !== "not_imported",
    resolvable: status === "offerable",
    compatible: status !== "incompatible",
    offerable: status === "offerable",
    status,
    reason:
      status === "offerable"
        ? null
        : status === "incompatible"
          ? "incompatible_for_material"
          : status === "not_imported"
            ? "profile_not_imported"
            : "not_resolvable",
    portal_label: null,
    provenance:
      status === "offerable"
        ? { source_system_tree_hash: "abcdef0123456789", orca_version: "2.3.2" }
        : { source_system_tree_hash: null, orca_version: null },
    ...overrides,
  };
  return base;
}

const MIXED_SLOTS: AdminProfileSlot[] = [
  slot("PLA", "aesthetic", "offerable"),
  slot("PLA", "standard", "offerable"),
  slot("PLA", "strong", "not_resolvable"),
  slot("PETG", "aesthetic", "not_imported"),
  slot("PETG", "standard", "offerable"),
  slot("PETG", "strong", "not_imported"),
  slot("PCTG", "aesthetic", "not_resolvable"),
  slot("PCTG", "standard", "offerable"),
  slot("PCTG", "strong", "not_imported"),
  slot("TPU", "aesthetic", "incompatible"),
  slot("TPU", "standard", "incompatible"),
  slot("TPU", "strong", "not_imported"),
];

describe("ProfileInventoryGrid (Story 33.1 — AC-12..AC-16)", () => {
  it("renders every one of the four statuses with an icon+text label (AC-13)", () => {
    renderGrid(MIXED_SLOTS);
    for (const label of ["Offerable", "Not imported", "Not resolvable", "Incompatible"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("shows a human-readable reason on a non-offerable cell, never on offerable (AC-12)", () => {
    renderGrid(MIXED_SLOTS);
    expect(
      screen.getAllByText("Not a valid process for TPU").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Installed profile fails to resolve").length,
    ).toBeGreaterThan(0);
  });

  it("exposes a provenance affordance only on offerable cells (AC-14)", () => {
    renderGrid(MIXED_SLOTS);
    const provenanceTriggers = screen.getAllByRole("button", {
      name: /show provenance/i,
    });
    const offerableCount = MIXED_SLOTS.filter((s) => s.offerable).length;
    expect(provenanceTriggers.length).toBe(offerableCount * 2);
  });

  it("never renders an Orca-internal key / path / g-code in the grid (AC-14 fence)", () => {
    const { container } = renderGrid(MIXED_SLOTS);
    const html = container.innerHTML;
    for (const forbidden of [
      "filament_max_volumetric_speed",
      "nozzle_temperature",
      "/intents/",
      ".json",
      "gcode",
      "settings_id",
      "bundle_hash",
    ]) {
      expect(html).not.toContain(forbidden);
    }
  });
});

describe("ProfileInventoryGrid import affordance (Story 33.2 — AC-16/AC-18)", () => {
  it("renders a LIVE (enabled) Import action on compatible not-imported cells", () => {
    renderGrid(MIXED_SLOTS);
    const importButtons = screen.getAllByRole("button", { name: "Import" });
    expect(importButtons.length).toBeGreaterThan(0);
    // 33.2: the placeholder is now a live action — no longer disabled.
    for (const btn of importButtons) {
      expect((btn as HTMLButtonElement).disabled).toBe(false);
    }
  });

  it("shows NO import action on incompatible cells (unchanged from 33.1)", () => {
    // A grid of only incompatible TPU cells must carry zero Import actions.
    renderGrid([
      slot("TPU", "aesthetic", "incompatible"),
      slot("TPU", "standard", "incompatible"),
    ]);
    expect(screen.queryByRole("button", { name: "Import" })).toBeNull();
  });

  it("posts the selected file as multipart to the import endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ...slot("PETG", "strong", "offerable") }), {
        status: 201,
      }),
    );
    renderGrid([slot("PETG", "strong", "not_imported")]);
    const input = screen.getAllByLabelText(
      /choose a profile json file to import/i,
    )[0] as HTMLInputElement;
    const file = new File(
      [JSON.stringify({ machine: {}, process: {}, filament: {} })],
      "triple.json",
      { type: "application/json" },
    );
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/admin/profiles/import");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    const form = init.body as FormData;
    expect(form.get("printer_ref")).toBe(PRINTER_REF);
    expect(form.get("material_class")).toBe("PETG");
    expect(form.get("quality_tier")).toBe("strong");
  });

  it("surfaces a localized rejection reason and does NOT flip the cell offerable (AC-18)", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: { reason_category: "invalid_partial", message: "bad" },
        }),
        { status: 422 },
      ),
    );
    renderGrid([slot("PETG", "strong", "not_imported")]);
    const input = screen.getAllByLabelText(
      /choose a profile json file to import/i,
    )[0] as HTMLInputElement;
    fireEvent.change(input, {
      target: { files: [new File(["x"], "x.json", { type: "application/json" })] },
    });

    expect(
      await screen.findAllByText(/isn't a valid profile triple/i),
    ).not.toHaveLength(0);
    // No optimistic flip: the cell never claims "Offerable".
    expect(screen.queryByText("Offerable")).toBeNull();
  });

  it("maps a too_large rejection to its localized message", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: { reason_category: "too_large", message: "big" },
        }),
        { status: 413 },
      ),
    );
    renderGrid([slot("PCTG", "strong", "not_imported")]);
    const input = screen.getAllByLabelText(
      /choose a profile json file to import/i,
    )[0] as HTMLInputElement;
    fireEvent.change(input, {
      target: { files: [new File(["x"], "x.json", { type: "application/json" })] },
    });
    expect(await screen.findAllByText(/too large to be a profile/i)).not.toHaveLength(0);
  });
});
