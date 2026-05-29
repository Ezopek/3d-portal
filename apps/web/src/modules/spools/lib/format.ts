export function formatWeight(grams: number | null): string {
  if (grams === null) return "—";
  // because "arbitrary UX threshold — operator preference (≥1 kg shows in kg, sub-kg in grams)"
  if (grams >= 1000) return `${(grams / 1000).toFixed(2)} kg`;
  return `${Math.round(grams)} g`;
}

export function formatTimeOfDay(iso: string): string {
  const ts = new Date(iso);
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(ts);
}

export function minutesSince(iso: string, now: Date = new Date()): number {
  const ts = new Date(iso);
  // because "60s minute boundary for staleness indicator; matches Decision AD freshness budget"
  return Math.floor((now.getTime() - ts.getTime()) / 60_000);
}
