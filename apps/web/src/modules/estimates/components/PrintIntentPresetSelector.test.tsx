import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { PrintIntentPresetInput } from "@/modules/estimates/lib/preset";
import { PrintIntentPresetSelector } from "./PrintIntentPresetSelector";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => {
  cleanup();
  fetchMock.mockReset();
});

const FILAMENT = {
  id: 10,
  name: "PLA Speed Matt White",
  vendor_id: 100,
  vendor_name: "Bambu Lab",
  material: "PLA",
  color_hex: "FFFFFF",
  price: 99.9,
  weight: 1000,
  spool_weight: 200,
};

function stubSpools() {
  fetchMock.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      spools: [],
      filaments: [FILAMENT],
      vendors: [],
      fetched_at: null,
      last_success_ts: null,
    }),
  });
}

function withQuery(node: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

const DEFAULT_PRESET: PrintIntentPresetInput = {
  material_class: "PLA",
  quality_tier: "standard",
  spoolman_filament_ref: null,
};

describe("PrintIntentPresetSelector (AC-2)", () => {
  it("emits a PrintIntentPreset-shaped object on material/tier change", () => {
    stubSpools();
    const calls: PrintIntentPresetInput[] = [];
    render(
      withQuery(
        <PrintIntentPresetSelector
          value={DEFAULT_PRESET}
          onChange={(p) => calls.push(p)}
        />,
      ),
    );
    fireEvent.change(screen.getByLabelText(/material/i), {
      target: { value: "PETG" },
    });
    fireEvent.change(screen.getByLabelText(/quality/i), {
      target: { value: "strong" },
    });
    expect(calls[0]).toEqual({ ...DEFAULT_PRESET, material_class: "PETG" });
    expect(calls[1]).toEqual({ ...DEFAULT_PRESET, quality_tier: "strong" });
  });

  it("never exposes a raw Orca key in any control or option", () => {
    stubSpools();
    const { container } = render(
      withQuery(
        <PrintIntentPresetSelector
          value={DEFAULT_PRESET}
          onChange={() => {}}
        />,
      ),
    );
    const html = container.innerHTML;
    for (const orca of [
      "filament_max_volumetric_speed",
      "layer_height",
      "nozzle_temperature",
      "bed_temp",
    ]) {
      expect(html).not.toContain(orca);
    }
  });

  it("renders material names verbatim in both locales (untranslated)", async () => {
    stubSpools();
    const { rerender } = render(
      withQuery(
        <PrintIntentPresetSelector
          value={DEFAULT_PRESET}
          onChange={() => {}}
        />,
      ),
    );
    for (const m of ["PLA", "PETG", "PCTG", "TPU"]) {
      expect(screen.getByRole("option", { name: m })).toBeTruthy();
    }
    await i18n.changeLanguage("pl");
    rerender(
      withQuery(
        <PrintIntentPresetSelector
          value={DEFAULT_PRESET}
          onChange={() => {}}
        />,
      ),
    );
    for (const m of ["PLA", "PETG", "PCTG", "TPU"]) {
      expect(screen.getByRole("option", { name: m })).toBeTruthy();
    }
    await i18n.changeLanguage("en");
  });

  it("pins by the stable profile ref, NOT the integer id", async () => {
    stubSpools();
    const calls: PrintIntentPresetInput[] = [];
    render(
      withQuery(
        <PrintIntentPresetSelector
          value={DEFAULT_PRESET}
          onChange={(p) => calls.push(p)}
        />,
      ),
    );
    // Wait for the filament list to load into the pin select.
    await waitFor(() =>
      expect(
        screen.getByRole("option", { name: "PLA Speed Matt White" }),
      ).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText(/pinned filament/i), {
      target: { value: "Bambu Lab\x1fPLA\x1fPLA Speed Matt White" },
    });
    expect(calls[0]?.spoolman_filament_ref).toBe(
      "Bambu Lab\x1fPLA\x1fPLA Speed Matt White",
    );
    expect(calls[0]?.spoolman_filament_ref).not.toBe("10");
  });

  it("gives every control a discernible label (a11y)", () => {
    stubSpools();
    render(
      withQuery(
        <PrintIntentPresetSelector
          value={DEFAULT_PRESET}
          onChange={() => {}}
        />,
      ),
    );
    expect(screen.getByLabelText(/material/i)).toBeTruthy();
    expect(screen.getByLabelText(/quality/i)).toBeTruthy();
    expect(screen.getByLabelText(/pinned filament/i)).toBeTruthy();
  });
});
