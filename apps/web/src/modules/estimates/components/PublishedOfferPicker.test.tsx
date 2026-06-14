import "@/locales/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/locales/i18n";
import type { MemberPublishedOfferView } from "@/lib/api-types";
import { PublishedOfferPicker } from "@/modules/estimates/components/PublishedOfferPicker";

// AC-12: populated state renders fieldset radiogroup with "None" first + each offer
// AC-13: no-offers state renders muted notice text, no radiogroup
// AC-14: transport error renders error text + Retry button
// AC-15: picker returns null when !isAuthenticated (no redirect)
// AC-22: all modules.member.offers.* keys are present in both locales

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

describe("PublishedOfferPicker", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("AC-12: renders fieldset radiogroup with None first and each offer", () => {
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

    // Fieldset group rendered
    expect(screen.getByRole("group")).toBeTruthy();
    // "None" option is first and checked by default
    const radios = screen.getAllByRole("radio");
    expect((radios[0] as HTMLInputElement).checked).toBe(true);
    // None + 2 offers = 3 radios
    expect(radios).toHaveLength(3);
    // Offer labels rendered
    expect(screen.getByText("K1 Max / Standard PLA")).toBeTruthy();
    expect(screen.getByText("K1 Max / Aesthetic PLA")).toBeTruthy();
  });

  it("AC-13: no-offers state renders nothing without radiogroup", () => {
    render(
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

    // No radiogroup when empty
    expect(screen.queryByRole("group")).toBeNull();
    expect(screen.queryByRole("radio")).toBeNull();
    // UX TL;DR: no compatible offers means the picker is absent, not a visible warning.
    expect(screen.queryByText(/No published profiles for/)).toBeNull();
  });

  it("AC-14: transport error renders error text + Retry button", () => {
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

    expect(screen.getByText(/Couldn't load published profiles/)).toBeTruthy();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    expect(retryBtn).toBeTruthy();
    retryBtn.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("AC-8/AC-15: picker renders null when isAuthenticated is false", () => {
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

  it("calls onSelect with the offer_id when an offer radio is selected", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      <PublishedOfferPicker
        offers={[OFFER_A]}
        selectedOfferId={null}
        onSelect={onSelect}
        isLoading={false}
        isError={false}
        onRetry={vi.fn()}
      />,
      { wrapper },
    );

    const radios = screen.getAllByRole("radio");
    // Click the first offer radio (index 1, after "None")
    await user.click(radios[1]!);
    expect(onSelect).toHaveBeenCalledWith(OFFER_A.offer_id);
  });
});

// AC-22: i18n parity check — all modules.member.offers.* keys exist in both locales
describe("i18n parity — modules.member.offers.*", () => {
  const REQUIRED_KEYS = [
    "modules.member.offers.picker.heading",
    "modules.member.offers.picker.none_option",
    "modules.member.offers.picker.none_option_aria",
    "modules.member.offers.picker.offer_aria",
    "modules.member.offers.picker.quality_label",
    "modules.member.offers.picker.printer_label",
    "modules.member.offers.picker.no_offers_for_material",
    "modules.member.offers.picker.loading",
    "modules.member.offers.picker.transport_error",
    "modules.member.offers.picker.retry",
    "modules.member.offers.estimate.not_computed_chip",
    "modules.member.offers.estimate.not_computed_title",
    "modules.member.offers.estimate.not_computed_detail",
    "modules.member.offers.estimate.offer_unavailable_chip",
    "modules.member.offers.estimate.offer_unavailable_title",
    "modules.member.offers.estimate.offer_unavailable_detail",
    "modules.member.offers.picker.region_label",
    "modules.member.offers.picker.selected_offer_aria",
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
