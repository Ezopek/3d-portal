// Story 32.6 (AC-4) — finite-number-guarded estimate formatters.
//
// Sibling to the spools `format.ts` (`formatWeight` em-dash-on-null discipline), but
// every formatter here additionally treats NaN / Infinity / -Infinity identically to a
// missing value. This is the defense-in-depth render-side gate over the backend
// `_reject_non_finite` persist gate (EstimateRecord): a transport/serialization edge
// must NEVER surface a poisoned digit string the operator could spend/print against.

// because "the no-silent-zero render contract (FR20-FAILURE-1 / EstimateRecord
// None-never-0) — a missing/non-finite numeric renders as the absence glyph, never a
// digit a caller could act on; mirrors the spools formatWeight em-dash convention".
export const EM_DASH = "—";

// The g↔kg / mm↔m display threshold. Arbitrary operator-UX preference mirroring the
// spools `formatWeight` ≥1000 convention — NOT a contractual value; revisit if operator
// preference changes. Marked explicitly arbitrary per the magic-constant rule.
const KILO_THRESHOLD = 1000;

/** Coerce to a finite number, or null for null/undefined/NaN/±Infinity. */
function finite(value: number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  if (!Number.isFinite(value)) return null;
  return value;
}

/** Duration `time_seconds` → "Xh Ym" / "Ym"; missing/non-finite/negative → em-dash. */
export function formatDuration(seconds: number | null | undefined): string {
  const s = finite(seconds);
  // A negative duration is physically meaningless — render absence, never "-Xm".
  if (s === null || s < 0) return EM_DASH;
  const totalMinutes = Math.round(s / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

/** Filament mass `filament_g` → "N g" / "N.NN kg"; missing/non-finite → em-dash. */
export function formatMass(grams: number | null | undefined): string {
  const g = finite(grams);
  if (g === null) return EM_DASH;
  if (g >= KILO_THRESHOLD) return `${(g / KILO_THRESHOLD).toFixed(2)} kg`;
  return `${Math.round(g)} g`;
}

/** Filament length `filament_mm` → "N mm" / "N.NN m"; missing/non-finite → em-dash. */
export function formatLength(mm: number | null | undefined): string {
  const v = finite(mm);
  if (v === null) return EM_DASH;
  if (v >= KILO_THRESHOLD) return `${(v / KILO_THRESHOLD).toFixed(2)} m`;
  return `${Math.round(v)} mm`;
}

/** Filament volume `filament_cm3` → "N.NN cm³"; missing/non-finite → em-dash. */
export function formatVolume(cm3: number | null | undefined): string {
  const v = finite(cm3);
  if (v === null) return EM_DASH;
  return `${v.toFixed(2)} cm³`;
}

/**
 * Informational cost `filament_cost` → "N.NN <currency>" (or a bare "N.NN" when no
 * currency is known); missing/non-finite → em-dash. The "informational, not a quote"
 * framing is an i18n label on the component (AC-9), not part of this string.
 */
export function formatCost(
  cost: number | null | undefined,
  currency: string | null | undefined,
): string {
  const c = finite(cost);
  if (c === null) return EM_DASH;
  const amount = c.toFixed(2);
  return currency ? `${amount} ${currency}` : amount;
}
