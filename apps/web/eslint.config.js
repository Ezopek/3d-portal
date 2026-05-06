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
      "no-restricted-syntax": [
        "error",
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
