import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";
import type { MemberPublishedOfferView } from "@/lib/api-types";
import { Button } from "@/ui/button";

interface Props {
  /**
   * The published offers for the current material. `null` when auth is not yet known
   * (renders nothing, AC-8/AC-15). An empty array renders the no-offers notice (AC-13).
   */
  offers: MemberPublishedOfferView[] | null;
  selectedOfferId: string | null;
  onSelect: (offerId: string | null) => void;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  /** When false the component renders null (§E.6, NFR24-AUTHGATE-1). */
  isAuthenticated?: boolean;
}

/**
 * Story 36.3 (AC-12/13/14/15) — member-facing published profile offer picker.
 *
 * Rendered inline in FilesTab between CatalogEstimateProfileSelector and the STL list.
 * Fails OPEN: transport error does not affect existing preset estimate flow (§E.5).
 * AuthGate discipline: returns null when !isAuthenticated — no redirect, no login prompt.
 * A11y: <fieldset> + <legend> + native radio inputs (arrow-key navigation, AC-26).
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

  // AC-8/AC-15: no render for unauthenticated visitors (AuthGate owns that case).
  if (!isAuthenticated) return null;

  // Loading is intentionally silent so the picker fails open and does not shift
  // the FilesTab while the offer list is still warming.
  if (isLoading) return null;

  // Transport error (§E.5) — fail OPEN; show Retry but don't block the preset flow.
  if (isError) {
    return (
      <div className="flex items-center gap-3">
        <p className="text-xs text-destructive">
          {t("modules.member.offers.picker.transport_error")}
        </p>
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          {t("modules.member.offers.picker.retry")}
        </Button>
      </div>
    );
  }

  // No offer data and no active pending/error state: render nothing (auth state or
  // parent gate not ready).
  if (offers === null) return null;

  // No compatible offers for the current material (§E.2) — absent, not an error.
  if (offers.length === 0) return null;

  // AC-12: populated state — fieldset radiogroup with "None" first, then each offer.
  return (
    <fieldset>
      <legend className="mb-1 text-xs font-medium text-muted-foreground">
        {t("modules.member.offers.picker.heading")}
      </legend>
      <div className="flex flex-wrap gap-2">
        {/* "None" option — default, restores preset mode */}
        <label
          className={cn(
            "flex cursor-pointer items-center gap-2 rounded border px-3 py-1.5 text-xs ring-inset",
            selectedOfferId === null
              ? "ring-1 ring-primary bg-primary/10 font-medium"
              : "border-border hover:bg-accent",
          )}
        >
          <input
            type="radio"
            name="offer-picker"
            value=""
            checked={selectedOfferId === null}
            onChange={() => onSelect(null)}
            aria-label={t("modules.member.offers.picker.none_option_aria")}
            className="sr-only"
          />
          {t("modules.member.offers.picker.none_option")}
        </label>

        {offers.map((offer) => (
          <label
            key={offer.offer_id}
            className={cn(
              "flex cursor-pointer flex-col rounded border px-3 py-1.5 text-xs ring-inset",
              selectedOfferId === offer.offer_id
                ? "ring-1 ring-primary bg-primary/10 font-medium"
                : "border-border hover:bg-accent",
            )}
          >
            <input
              type="radio"
              name="offer-picker"
              value={offer.offer_id}
              checked={selectedOfferId === offer.offer_id}
              onChange={() => onSelect(offer.offer_id)}
              aria-label={t("modules.member.offers.picker.offer_aria", {
                label: offer.portal_label,
              })}
              className="sr-only"
            />
            <span className="font-medium">{offer.portal_label}</span>
            <span className="mt-0.5 flex flex-wrap gap-2 text-muted-foreground">
              {offer.quality_tier !== null && (
                <span>
                  {t("modules.member.offers.picker.quality_label", {
                    tier: t(`modules.estimates.quality.${offer.quality_tier}`),
                  })}
                </span>
              )}
              {offer.printer_name !== null && (
                <span>
                  {t("modules.member.offers.picker.printer_label", {
                    printer: offer.printer_name,
                  })}
                </span>
              )}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
