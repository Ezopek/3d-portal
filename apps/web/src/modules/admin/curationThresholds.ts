// Story 52.3 (D-2) — the curation thresholds, declared exactly ONCE.
//
// Both the replace-set editor (ModelCategoriesDialog) and the curation-QA panel
// render a judgement about the same number on the same screen. Two independent
// literals would let one surface accept a set without warning while the other
// flags the same model — a defect the constant simply avoids.
//
// A non-component module rather than an export from ModelCategoriesDialog.tsx:
// `react-refresh/only-export-components` is a `warn` under `--max-warnings=0`,
// so a non-component export from a component file fails lint. `duplicateTags.ts`
// is the precedent for a sibling helper module in this folder.

/**
 * The advisory norm from FR26-CAT-3: 1-3 categories per model. Above this the
 * editor WARNS and still saves, and the QA panel raises an advisory finding.
 * There is no hard database maximum and no write-blocking enforcement, so
 * neither surface may present this as a limit.
 *
 * NOT to be edited in place: the value is grounded in the eight-category
 * shipped vocabulary (>3 is more than 37.5% of it). If the vocabulary grows
 * past roughly 16 categories the norm is re-derived via `bmad-correct-course`
 * against FR26-CAT-3.
 */
export const ADVISORY_MAX = 3;

/**
 * A category with 1-2 models is "behaving like a narrow tag". This is the exact
 * complement of Story 49.2's admission bar (each category should land >= 3
 * models under deliberate curation), not an independently invented number.
 * `model_count === 0` is a distinct finding (empty), never also a tiny one.
 */
export const TINY_MAX = 2;
