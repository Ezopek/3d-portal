import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import prettierConfig from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "**/*.gen.ts",
      "**/*.config.{ts,js}",
      "**/*.config.d.ts",
      "**/playwright.config.ts",
      "tests/visual/__snapshots__/**",
      "test-results/**",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  react.configs.flat.recommended,
  react.configs.flat["jsx-runtime"],
  {
    files: ["src/**/*.{ts,tsx}", "tests/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    settings: {
      react: { version: "detect" },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "react/no-unknown-property": [
        "error",
        { ignore: ["camera-controls", "auto-rotate", "shadow-intensity", "exposure", "tone-mapping", "environment-image", "skybox-image", "ar", "ar-modes", "ios-src"] },
      ],
      // Severity is `warn` shared across all selectors. The legacy /api/files|catalog
      // patterns have zero current violations (migrated in d92e551) so warn vs error
      // makes no practical difference under the `--max-warnings=N` gate. The color-literal
      // patterns (Initiative 3, Story E5.4) coexist at warn; the Phase A audit found
      // 10 known violations remediated by Stories E5.7/E5.8/E5.10. `--max-warnings=10`
      // in package.json `lint` script accommodates them during Phase B; Story E5.10
      // closing commit restores `--max-warnings=0`. See architecture.md § Initiative 3
      // § Decision C.
      "no-restricted-syntax": [
        "warn",
        {
          selector: "Literal[value=/^\\/api\\/(files|catalog)\\//]",
          message:
            "Legacy API surface /api/files/* and /api/catalog/* was removed in commit d92e551. Use the SoT API: /api/models/{id}/files/{file_id}/content.",
        },
        {
          selector: "TemplateElement[value.raw=/\\/api\\/(files|catalog)\\//]",
          message:
            "Legacy API surface /api/files/* and /api/catalog/* was removed in commit d92e551. Use the SoT API: /api/models/{id}/files/{file_id}/content.",
        },
        // Initiative 3 — color-literal bans (Story E5.4, FR4).
        // Severity is error (shared with the legacy bans above). The 11 known
        // Phase-A violations are accommodated by a temporarily-relaxed
        // `--max-warnings` in apps/web/package.json `lint` script; Story E5.10
        // closing commit restores `--max-warnings=0` after stories 5.7/5.8/5.10
        // remediate. See architecture.md § Initiative 3 § Decision C.
        {
          selector:
            "JSXAttribute[name.name='className'] Literal[value=/(?:^|\\s)(?:bg|text|border|fill|stroke|ring|from|to|via|shadow|outline|decoration|caret|accent|placeholder)-\\[(?:#|rgb|hsl|oklch|color\\()/]",
          message:
            "Color literals in className are forbidden. Use a theme token (bg-card, text-foreground, bg-overlay, etc.) or add a new --color-* token to apps/web/src/styles/theme.css. See Initiative 3 (UI theme compliance) — _bmad-output/planning-artifacts/architecture.md § Decision C.",
        },
        {
          selector:
            "JSXAttribute[name.name='className'] TemplateElement[value.raw=/(?:^|\\s)(?:bg|text|border|fill|stroke|ring|from|to|via|shadow|outline|decoration|caret|accent|placeholder)-\\[(?:#|rgb|hsl|oklch|color\\()/]",
          message:
            "Color literals in className are forbidden. Use a theme token or add a new --color-* token to theme.css. See Initiative 3 (UI theme compliance).",
        },
        {
          selector:
            "JSXAttribute[name.name='className'] Literal[value=/(?:^|\\s)(?:bg|text|border)-(?:red|blue|green|zinc|gray|slate|stone|neutral|amber|yellow|orange|emerald|lime|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950)\\b/]",
          message:
            "Raw Tailwind palette utilities (bg-zinc-900, text-red-500, etc.) are forbidden. Use a theme token (bg-card, bg-destructive, etc.) or add a new --color-* token to theme.css. See Initiative 3.",
        },
        {
          selector:
            "JSXAttribute[name.name='className'] TemplateElement[value.raw=/(?:^|\\s)(?:bg|text|border)-(?:red|blue|green|zinc|gray|slate|stone|neutral|amber|yellow|orange|emerald|lime|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950)\\b/]",
          message:
            "Raw Tailwind palette utilities are forbidden. Use a theme token or add a new --color-* token to theme.css.",
        },
        {
          selector:
            "JSXAttribute[name.name='className'] Literal[value=/(?:^|\\s)(?:bg|text)-(?:white|black)\\b/]",
          message:
            "Raw bg-white/bg-black/text-white/text-black are forbidden. Use a theme token (bg-background, text-foreground, etc.) so light and dark themes are honored.",
        },
        {
          selector:
            "JSXAttribute[name.name='className'] TemplateElement[value.raw=/(?:^|\\s)(?:bg|text)-(?:white|black)\\b/]",
          message:
            "Raw bg-white/bg-black/text-white/text-black are forbidden. Use a theme token (bg-background, text-foreground, etc.) so light and dark themes are honored.",
        },
      ],
    },
  },
  {
    // shadcn/ui colocates `cva()` variants next to the component; shell colocates
    // a context provider with its consumer hook. Both break Fast Refresh in
    // theory but are stable, dev-time-only files we accept the trade-off on.
    files: ["src/ui/**/*.{ts,tsx}", "src/shell/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  {
    // React Three Fiber declares custom JSX intrinsic elements (e.g. <mesh>,
    // <ambientLight>) with three.js property names that ESLint can't know
    // about. Disable the unknown-property check for the viewer module only.
    files: ["src/modules/catalog/components/viewer3d/**/*.{ts,tsx}"],
    rules: {
      "react/no-unknown-property": "off",
    },
  },
  {
    files: ["tests/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  prettierConfig,
);
