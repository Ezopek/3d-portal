#!/usr/bin/env node
/* global console, process */
import { access, mkdir, stat } from "node:fs/promises";
import { constants } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(__dirname, "..");

const DEFAULT_CHROMIUM_CANDIDATES = [
  "/usr/local/bin/chromium",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
];

const args = new Set(process.argv.slice(2));

function usage() {
  console.log(`Usage: npm run design-sync -- [options]

Regenerate and upload the Claude Design sync bundle for portal-web.
Run from apps/web or the repo root; this script resolves paths itself.

Options:
  --skip-build       Do not run npm run build before prepare.sh
  --skip-install     Do not install .ds-sync dependencies; assumes they already exist
  --check            Validate local prerequisites and print planned commands only
  -h, --help         Show this help

Environment:
  DS_CHROMIUM_PATH   Chromium binary for converter capture/validation

Expected durable inputs:
  .design-sync/config.json
  .design-sync/prepare.sh
  .design-sync/previews/**
  .design-sync/providers/**
  .design-sync/fonts/**

Expected local converter staging:
  .ds-sync/resync.mjs and .ds-sync/package.json

If .ds-sync is missing, re-run Claude /design-sync once to stage the converter,
or follow .design-sync/NOTES.md § "Re-sync from a fresh checkout".
`);
}

if (args.has("--help") || args.has("-h")) {
  usage();
  process.exit(0);
}

const checkOnly = args.has("--check");
const skipBuild = args.has("--skip-build");
const skipInstall = args.has("--skip-install");

async function exists(file) {
  try {
    await access(path.join(webRoot, file), constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

async function executable(file) {
  try {
    await access(file, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

async function findChromium() {
  if (process.env.DS_CHROMIUM_PATH) return process.env.DS_CHROMIUM_PATH;
  for (const candidate of DEFAULT_CHROMIUM_CANDIDATES) {
    if (await executable(candidate)) return candidate;
  }
  return null;
}

function run(command, cmdArgs, options = {}) {
  const pretty = [command, ...cmdArgs].join(" ");
  if (checkOnly) {
    console.log(`[check] would run: ${pretty}`);
    return Promise.resolve();
  }
  console.log(`→ ${pretty}`);
  return new Promise((resolve, reject) => {
    const child = spawn(command, cmdArgs, {
      cwd: webRoot,
      stdio: "inherit",
      shell: false,
      env: { ...process.env, ...options.env },
    });
    child.on("exit", (code, signal) => {
      if (code === 0) resolve();
      else reject(new Error(`${pretty} failed with ${signal ?? `exit ${code}`}`));
    });
    child.on("error", reject);
  });
}

async function requireFile(file, hint) {
  if (await exists(file)) return;
  throw new Error(`Missing ${file}. ${hint}`);
}

async function ensureDsSyncDeps() {
  const hasPackageJson = await exists(".ds-sync/package.json");
  const hasEsbuild = await exists(".ds-sync/node_modules/esbuild");

  if (!hasPackageJson) {
    throw new Error("Missing .ds-sync/package.json. Stage the converter as described in .design-sync/NOTES.md.");
  }

  if (hasEsbuild) return;

  if (skipInstall) {
    throw new Error(
      "Missing .ds-sync/node_modules/esbuild and --skip-install was set. Run `npm install --prefix .ds-sync` or omit --skip-install.",
    );
  }

  await run("npm", ["install", "--prefix", ".ds-sync"]);
}

async function main() {
  console.log(`design-sync: portal-web at ${webRoot}`);

  await requireFile("package.json", "Run this script inside apps/web or keep the repo layout intact.");
  await requireFile(".design-sync/config.json", "PR #4 design-sync durable config is required.");
  await requireFile(".design-sync/prepare.sh", "PR #4 design-sync prepare script is required.");
  await requireFile(".ds-sync/resync.mjs", "Stage the converter first: re-run Claude /design-sync or see .design-sync/NOTES.md.");
  await requireFile(".ds-sync/package.json", "Stage the converter dependencies manifest from the /design-sync skill.");

  const chromium = await findChromium();
  if (!chromium) {
    throw new Error("No Chromium found. Set DS_CHROMIUM_PATH, e.g. DS_CHROMIUM_PATH=/usr/local/bin/chromium.");
  }
  console.log(`design-sync: using Chromium at ${chromium}`);

  if (!skipBuild) {
    await run("npm", ["run", "build"]);
  }

  await run("bash", [".design-sync/prepare.sh"]);
  await ensureDsSyncDeps();

  await mkdir(path.join(webRoot, "ds-bundle"), { recursive: true });

  await run("node", [
    ".ds-sync/resync.mjs",
    "--config",
    ".design-sync/config.json",
    "--node-modules",
    "./node_modules",
    "--out",
    "./ds-bundle",
    "--remote",
    ".design-sync/.cache/remote-sync.json",
  ], { env: { DS_CHROMIUM_PATH: chromium } });

  if (!checkOnly) {
    const bundle = await stat(path.join(webRoot, "ds-bundle")).catch(() => null);
    console.log(`✓ design-sync complete${bundle ? " — ds-bundle refreshed" : ""}`);
  }
}

main().catch((error) => {
  console.error(`✗ design-sync failed: ${error.message}`);
  process.exit(1);
});
