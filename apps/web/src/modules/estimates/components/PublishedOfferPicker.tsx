import { useId } from "react";
import { useTranslation } from "react-i18next";

import type { MemberPublishedOfferView } from "@/lib/api-types";
import { Button } from "@/ui/button";

interface Props {
  /**
   * The published offers for the current material. `null` when auth is not yet known
   * (renders nothing, AC-8/AC-12). An empty array renders nothing (AC-3).
   */
  offers: MemberPublishedOfferView[] | null;
  selectedOfferId: string | null;
  onSelect: (offerId: string | null) => void;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  /** When false the component renders null (AC-12, NFR24-AUTHGATE-1). */
  isAuthenticated?: boolean;
}

/**
 * Story 36.4 — compact member-facing offer picker.
 *
 * Renders as a label + <select> flex item designed to sit inside
 * CatalogEstimateProfileSelector's children slot — one unified estimate profile bar.
 *
 * Replaces the 36.3 large radio/card layout (operator correction 2026-06-14).
 * Fails OPEN: transport error never blocks the existing preset estimate flow.
 * AuthGate discipline: returns null when !isAuthenticated — no redirect, no login prompt.
 * printer_name is intentionally NOT shown (AC-6/AC-14); only portal_label is used.
 */
export function PublishedOfferPicker({
  offers,
  selectedOfferId,
  onSelect,
  isLoading,
  isError,
  onRetry,
  isAuthenticated = true,
}: Props) {
  const { t } = useTranslation();
  const selectId = useId();

  // AC-12: no render for unauthenticated visitors (AuthGate owns that case).
  if (!isAuthenticated) return null;

  // AC-8: loading is intentionally silent so the picker fails open without layout shift.
  if (isLoading) return null;

  // AC-9: transport error — fail OPEN; compact inline notice + Retry; preset flow unaffected.
  if (isError) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-destructive">
          {t("modules.member.offers.picker.transport_error")}
        </span>
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          {t("modules.member.offers.picker.retry")}
        </Button>
      </div>
    );
  }

  // No offer data (auth/parent gate not ready) or empty list (AC-3) — render nothing.
  if (offers === null || offers.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={selectId} className="shrink-0 text-xs text-muted-foreground">
        {t("modules.member.offers.picker.select_label")}
      </label>
      <select
        id={selectId}
        className="rounded-md border bg-background px-2 py-1 text-xs text-foreground"
        value={selectedOfferId ?? ""}
        onChange={(e) => {
          const val = e.target.value;
          onSelect(val === "" ? null : val);
        }}
      >
        <option value="">{t("modules.member.offers.picker.none_option")}</option>
        {offers.map((offer) => (
          // FUTURE: when MemberPublishedOfferView adds a multilingual description field,
          // consider using it here instead of portal_label. printer_name is deliberately
          // excluded from member UI (AC-14).
          <option key={offer.offer_id} value={offer.offer_id}>
            {offer.portal_label}
          </option>
        ))}
      </select>
    </div>
  );
}
