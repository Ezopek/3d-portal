# design-sync notes — portal-web (3D Portal Web UI)

Repo-specific gotchas for future syncs. Commands run **from `apps/web/`** (the package
root); `.design-sync/`, `.ds-sync/`, `ds-bundle/` all live under `apps/web/`.

## Source shape & build

- This is an **application** (`apps/web`), not a library — there is **no library build**
  that exports the components as a module. The converter runs in **synth/override-entry
  mode**: a barrel at `.design-sync/.cache/ds-entry.tsx` re-exports every non-test
  `src/ui/**/*.tsx` and is passed via `cfg.entry`. The barrel also does a side-effect
  `import "../../src/locales/i18n"` so the **global react-i18next instance is initialized**
  in the bundle (the app has no `<I18nextProvider>` — it relies on `initReactI18next`), so
  `useTranslation()` returns real translations in previews with no `cfg.provider`.
- **`bash .design-sync/prepare.sh`** (committed) regenerates the two gitignored derived
  inputs the converter reads: the barrel `.cache/ds-entry.tsx` (component set + global pl
  i18n) and `.cache/app.css` (a copy of the newest `dist/assets/index-*.css`). Run it after
  `npm run build` and before the converter. `cfg.entry` and `cfg.cssEntry` point at those two
  `.cache/` files — so **the Vite CSS hash is never pinned in config** (prepare.sh resolves
  the current one each run); adding/removing a `src/ui` component is likewise just a re-run.
- `cfg.componentSrcMap` pins exactly the carded components; `exportedNames` is empty
  (no `.d.ts` tree), so those pins ARE the card list. The bundle still re-exports every
  subcomponent (CardContent, DialogTrigger, …) for composition.
- `PKG_DIR` resolves to `apps/web` via the walk-up from the barrel's path
  (`.design-sync/.cache/` → `apps/web/package.json` has `name: portal-web`). Do NOT remove
  `apps/web/package.json`'s `name`.

## Render check / chromium

- No bundled chromium-1217 (only headless_shell). Run validate/capture with
  `DS_CHROMIUM_PATH=/usr/local/bin/chromium` (Chrome for Testing 148, system).

## Fonts

- The app declares `--font-sans: "Inter"` but **never ships Inter** (relies on the OS font;
  falls back to system-ui). We ship Inter ourselves: `.design-sync/fonts/` holds 8 woff2
  (latin + latin-ext, weights 400/500/600/700 — latin-ext carries the Polish glyphs) plus
  `inter.css`, wired via `cfg.extraFonts`. SIL OFL 1.1. **User approved shipping Inter.**

## DS gaps / findings (surface to maintainers)

- **`--color-secondary` / `--color-secondary-foreground`** are now defined in
  `src/styles/theme.css` (light + dark, story `t_3894e508`). The `secondary` variant of
  `Button`/`Badge` — and the `SourceBadge` component, which hardcodes `variant="secondary"` —
  now render with a muted neutral fill in both themes. Previously undefined (rendered unstyled);
  the conventions header and previews may safely use `secondary` again.

## Known render warns

- `[RENDER_THIN]` on **Dialog**, **ConfirmDialog**, **Sheet** — these render their content in a
  portal with `position: fixed`, so the mounted root measures 0px height even though the
  screenshot is correct (verified manually). Benign — not a render failure.
- **ModelViewer** is excluded from the carded set (`componentSrcMap: {"ModelViewer": null}`)
  because it wraps the `<model-viewer>` web component, which is loaded from a googleapis
  `<script>` in the app's index.html and needs WebGL + a real model file — none of which exist
  in the headless preview / Claude Design environment (it renders a flat muted box → tripped
  `[RENDER_BLANK]`). It is still exported by the bundle (importable by the design agent); it
  just has no preview card.

## Preview providers / locale

- `.design-sync/providers/ds-providers.tsx` exports **DsProviders**, shipped into the bundle
  via `cfg.extraEntries`. It wraps children in a TanStack `RouterContextProvider` so components
  that render `<Link>` (e.g. **ModelCard**) resolve their router context. It MUST be in the
  bundle (not imported fresh in a preview) so it shares the bundle's `@tanstack/react-router`
  instance — context identity is what makes `<Link>` work. Wrap such previews:
  `<DsProviders><ModelCard … /></DsProviders>`.
- The barrel calls `i18n.changeLanguage("pl")` so previews render in **Polish** (brand
  default). Headless chromium's `navigator.language` is en, which the app's LanguageDetector
  would otherwise pick — that produced English labels. Forcing pl keeps i18n text consistent
  with the hardcoded Polish copy in the previews.
- **CardCarousel** images come from `/api/models/.../content` (404 offline) — the preview shows
  the carousel chrome (arrows + dots) over the muted placeholder; a small viewport override
  keeps the hover-gated arrows visible.
- **LoadingState** and **Tabs** use `cardMode: "column"` overrides so their wider stories render
  at full card width instead of overflowing the default grid cells.

## Re-sync from a fresh checkout (repo → resync)

The committed durable set is `config.json`, `NOTES.md`, `conventions.md`, `prepare.sh`,
`previews/`, `providers/`, `fonts/`. The converter scripts (`.ds-sync/`), the build output
(`ds-bundle/`) and the derived inputs (`.design-sync/.cache/`) are gitignored and regenerated.
Full path on a clean clone:

```sh
cd apps/web
npm ci                       # app deps (incl. @tanstack/react-router for the provider)

# Stage the converter from the /design-sync skill (it owns the converter; not committed).
# Easiest: re-run `/design-sync` — it stages .ds-sync/ and installs deps. Or manually:
mkdir -p .ds-sync && cp -r <skill>/{package-build,package-validate,package-capture,resync}.mjs <skill>/lib <skill>/storybook .ds-sync/
echo '{"name":"ds-sync-deps","private":true}' > .ds-sync/package.json
(cd .ds-sync && npm i esbuild ts-morph @types/react)

npm run design-sync          # build → prepare.sh → .ds-sync/resync.mjs → ds-bundle + remote-sync
```

`npm run design-sync:check` validates paths and prints the planned commands without running the
build/converter. Set `DS_CHROMIUM_PATH=/usr/local/bin/chromium` if auto-detection ever picks the
wrong browser.

Fonts are committed under `.design-sync/fonts/`, so a fresh checkout needs **no** `@fontsource`
install. The app's `eslint.config.js` ignores `.design-sync/`, `.ds-sync/`, `ds-bundle/` so the
lint gate stays green with the sync inputs present.

## Re-sync risks

- The compiled app CSS is the source of all component utility classes; `prepare.sh` re-copies
  the newest `dist/assets/index-*.css`, so it must run **after** `npm run build`. A stale or
  missing `dist/` → stale or absent `.cache/app.css`.
- Previews depend on the bundled global react-i18next instance (barrel side-effect, forced pl)
  and on `DsProviders` sharing the bundle's `@tanstack/react-router` instance — both come from
  the app's own source via the synth-entry barrel, not a library build.
- `ds-providers.tsx` and the `model` fixture in `previews/ModelCard.tsx` are tied to the
  current router/`ModelSummary` shapes; a breaking upstream change there needs a preview update.
