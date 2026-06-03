interface Props {
  className?: string;
}

/**
 * EST-DISPLAY-1 — a tasteful inline filament-spool glyph for the estimate chip.
 *
 * Lucide has no canonical spool glyph (UX §B), so this is a small custom SVG: a spool
 * (two flanges + a core) wound with filament. `stroke="currentColor"` so it inherits the
 * chip's text color for free dark/light + per-state tinting; `aria-hidden` because the chip's
 * accessible meaning is carried by its text/`title`, not the icon (UX accessibility note).
 */
export function SpoolIcon({ className }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {/* Left + right spool flanges. */}
      <line x1="5" y1="4" x2="5" y2="20" />
      <line x1="19" y1="4" x2="19" y2="20" />
      {/* The wound filament body between the flanges. */}
      <rect x="8" y="8" width="8" height="8" rx="1" />
      {/* Core axle hinting the wind direction. */}
      <line x1="8" y1="12" x2="16" y2="12" />
    </svg>
  );
}
