import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { MemberPublishedOfferView } from "@/lib/api-types";
import { PublishedOfferPicker } from "@/modules/estimates/components/PublishedOfferPicker";

// Story 36.4 compact offer picker test suite.
// Key new assertions vs 36.3:
//   - No radiogroup / fieldset; instead a native <select>
//   - printer_name NOT present in any rendered text (AC-6/AC-14)
//   - Standard estimate fallback <option> always first
//   - onSelect called with offer_id on change
//   - error/fail-open preserved
//   - i18n parity with updated key list including select_label

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const OFFER_A: MemberPublishedOfferView = {
  offer_id: "a".repeat(32),
  portal_label: "K1 Max / Standard PLA",
  quality_tier: "standard",
  compatible_material_categories: ["PLA"],
  printer_name: "K1 Max",
};

const OFFER_B: MemberPublishedOfferView = {
  offer_id: "b".repeat(32),
  portal_label: "K1 Max / Aesthetic PLA",
  quality_tier: "aesthetic",
  compatible_material_categories: ["PLA"],
  printer_name: null,
};

describe("PublishedOfferPicker (compact select)", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("AC-5/AC-6: renders a select with 'Standard estimate' first, then offer portal_labels", () => {
    render(
      <PublishedOfferPicker
        offers={[OFFER_A, OFFER_B]}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select).toBeTruthy();
    const options = Array.from(select.options);
    expect(options[0]!.value).toBe("");
    expect(options[0]!.text).toMatch(/Standard estimate/i);
    expect(options[1]!.text).toBe("K1 Max / Standard PLA");
    expect(options[2]!.text).toBe("K1 Max / Aesthetic PLA");
  });

  it("AC-14: printer_name is NOT shown in any rendered text", () => {
    const { container } = render(
      <PublishedOfferPicker
        offers={[OFFER_A]}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    // printer_name "K1 Max" is part of portal_label — that's OK.
    // But it must NOT appear as standalone printer metadata (no "Printer: K1 Max" text).
    const text = container.textContent ?? "";
    expect(text).not.toMatch(/Printer:/i);
    expect(text).not.toMatch(/Drukarka:/i);
  });

  it("AC-5: 'Standard estimate' option is selected when selectedOfferId is null", () => {
    render(
      <PublishedOfferPicker
        offers={[OFFER_A]}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("");
  });

  it("AC-7: onSelect called with offer_id when an offer option is selected", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <PublishedOfferPicker
        offers={[OFFER_A, OFFER_B]}
        selectedOfferId={null}
        onSelect={onSelect}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    const select = screen.getByRole("combobox");
    await user.selectOptions(select, OFFER_A.offer_id);
    expect(onSelect).toHaveBeenCalledWith(OFFER_A.offer_id);
  });

  it("AC-7: onSelect called with null when 'Standard estimate' option is selected", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <PublishedOfferPicker
        offers={[OFFER_A]}
        selectedOfferId={OFFER_A.offer_id}
        onSelect={onSelect}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "");
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("AC-3/AC-8: renders nothing when offers list is empty", () => {
    const { container } = render(
      <PublishedOfferPicker
        offers={[]}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    expect(container.firstChild).toBeNull();
  });

  it("AC-8: renders nothing while loading (silent fail-open)", () => {
    const { container } = render(
      <PublishedOfferPicker
        offers={null}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={true}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    expect(container.firstChild).toBeNull();
  });

  it("AC-9: transport error renders compact error text + Retry button", () => {
    const onRetry = vi.fn();
    render(
      <PublishedOfferPicker
        offers={[]}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={false}
        isError={true}
        onRetry={onRetry}
      />,
      { wrapper },
    );

    expect(screen.getByText(/Couldn't load published profiles/i)).toBeTruthy();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeTruthy();
    retryBtn.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("AC-12: renders null when isAuthenticated is false", () => {
    const { container } = render(
      <PublishedOfferPicker
        offers={null}
        selectedOfferId={null}
        onSelect={vi.fn()}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
        isAuthenticated={false}
      />,
      { wrapper },
    );

    expect(container.firstChild).toBeNull();
  });
});

// AC-18/AC-19: i18n parity — all required offer picker keys in both locales
describe("i18n parity — modules.member.offers.*", () => {
  const REQUIRED_KEYS = [
    "modules.member.offers.picker.select_label",
    "modules.member.offers.picker.none_option",
    "modules.member.offers.picker.transport_error",
    "modules.member.offers.picker.retry",
    "modules.member.offers.picker.heading",
    "modules.member.offers.picker.none_option_aria",
    "modules.member.offers.picker.offer_aria",
    "modules.member.offers.picker.no_offers_for_material",
    "modules.member.offers.picker.loading",
    "modules.member.offers.picker.region_label",
    "modules.member.offers.picker.selected_offer_aria",
    "modules.member.offers.estimate.not_computed_chip",
    "modules.member.offers.estimate.not_computed_title",
    "modules.member.offers.estimate.not_computed_detail",
    "modules.member.offers.estimate.offer_unavailable_chip",
    "modules.member.offers.estimate.offer_unavailable_title",
    "modules.member.offers.estimate.offer_unavailable_detail",
  ];

  it("all required offer picker keys exist in en.json", async () => {
    await i18n.changeLanguage("en");
    for (const key of REQUIRED_KEYS) {
      const result = i18n.t(key);
      expect(result, `Missing EN key: ${key}`).not.toBe(key);
    }
  });

  it("all required offer picker keys exist in pl.json", async () => {
    await i18n.changeLanguage("pl");
    for (const key of REQUIRED_KEYS) {
      const result = i18n.t(key);
      expect(result, `Missing PL key: ${key}`).not.toBe(key);
    }
    await i18n.changeLanguage("en");
  });
});
