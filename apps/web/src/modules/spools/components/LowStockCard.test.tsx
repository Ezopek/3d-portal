import { describe, expect, it } from "vitest";

import { LOW_STOCK_THRESHOLD_G, selectLowStockRows } from "./LowStockCard.lib";
import type { FilamentView, SpoolView } from "@/lib/api-types";

const baseFilament: FilamentView = {
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

function spool(overrides: Partial<SpoolView>): SpoolView {
  return {
    id: 1,
    filament_id: 10,
    price: null,
    remaining_weight: 500,
    initial_weight: 1000,
    used_weight: 500,
    spool_weight: 200,
    first_used: null,
    last_used: null,
    archived: false,
    lot_nr: null,
    ...overrides,
  };
}

describe("LOW_STOCK_THRESHOLD_G", () => {
  it("is 200g (operator UX preference)", () => {
    expect(LOW_STOCK_THRESHOLD_G).toBe(200);
  });
});

describe("selectLowStockRows", () => {
  it("filters spools by threshold", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, remaining_weight: 138.9 }),
        spool({ id: 2, remaining_weight: 850 }),
        spool({ id: 3, remaining_weight: 163.2 }),
      ],
      [baseFilament],
    );
    expect(rows.map((r) => r.spool.id)).toEqual([1, 3]);
  });

  it("excludes archived spools even if below threshold", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, remaining_weight: 10, archived: true }),
        spool({ id: 2, remaining_weight: 138.9 }),
      ],
      [baseFilament],
    );
    expect(rows.map((r) => r.spool.id)).toEqual([2]);
  });

  it("excludes spools with null remaining_weight", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, remaining_weight: null }),
        spool({ id: 2, remaining_weight: 138.9 }),
      ],
      [baseFilament],
    );
    expect(rows.map((r) => r.spool.id)).toEqual([2]);
  });

  it("sorts low-stock rows by remaining_weight ascending", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, remaining_weight: 163.2 }),
        spool({ id: 2, remaining_weight: 138.9 }),
      ],
      [baseFilament],
    );
    expect(rows.map((r) => r.spool.id)).toEqual([2, 1]);
  });

  it("attaches the matching filament to each row (or undefined when missing)", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, filament_id: 10, remaining_weight: 138.9 }),
        spool({ id: 2, filament_id: 99, remaining_weight: 100 }),
      ],
      [baseFilament],
    );
    // Sorted ascending by remaining_weight → row 0 is the orphaned spool 2.
    expect(rows[0]?.spool.id).toBe(2);
    expect(rows[0]?.filament).toBeUndefined();
    expect(rows[1]?.spool.id).toBe(1);
    expect(rows[1]?.filament?.id).toBe(10);
  });

  it("excludes a spool sitting exactly on the threshold (boundary is strict <)", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, remaining_weight: 200 }),
        spool({ id: 2, remaining_weight: 199.9 }),
      ],
      [baseFilament],
    );
    expect(rows.map((r) => r.spool.id)).toEqual([2]);
  });

  it("returns an empty list when every spool is above the threshold", () => {
    const rows = selectLowStockRows(
      [
        spool({ id: 1, remaining_weight: 500 }),
        spool({ id: 2, remaining_weight: 850 }),
      ],
      [baseFilament],
    );
    expect(rows).toEqual([]);
  });
});
