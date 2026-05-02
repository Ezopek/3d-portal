# Catalog 3MF → STL migration

Design for a one-shot migration of the 3D model catalog plus a permanent
workflow rule that converts every incoming `.3mf` to STL on entry. The
catalog lives at `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/` (Nextcloud-
synced); its vendor-neutral source of truth is its own `AGENTS.md`.

## Motivation

- Loose model files (`*.stl`, `*.3mf`, `*.step`) sitting directly in
  category directories instead of per-model folders break the catalog
  convention and the portal's per-model URL scheme.
- `.3mf` files downloaded from Printables / Thangs / MakerWorld carry
  embedded slicer profiles for unrelated printers. OrcaSlicer auto-loads
  them when opening the file, contaminating the local profile list. The
  catalog owner wants none of these in the live catalog.
- The catalog's `wlasne modele/` (own models) directory has accumulated
  FreeCAD source files that are no longer wanted. Only `mosfet_hw-700_case`
  (STEP-only) is worth keeping.

## Scope

**In scope:**
1. One-shot migration of the existing catalog: wrap loose files in
   per-model folders, convert orphan 3MFs to STLs, archive 3MF
   originals, clean up `wlasne modele/`, update `_index/index.json`.
2. New permanent rule: every 3MF added to the catalog (via URL workflow
   or manual drop) is converted to STL on entry, original archived. No
   exceptions for `premium/`.
3. AGENTS.md (catalog) updated to document the new rule and removed
   `own_models` category.
4. `sync-data.sh` updated to exclude `_archive/` from rsync to the
   portal data volume.

**Out of scope:**
- Re-categorizing or renaming existing model folders.
- Changes to the portal's `_index/index.json` schema.
- Migration of STEP files (kept where they are; they originate from
  parametric CAD and have no valid mesh-to-BRep round trip).
- Modifying `wlasne modele/podstawka_laptop_latitude_5450.*` or
  `wlasne modele/test_spiecia.*` for any reason other than deletion.

## Decisions made (during brainstorming)

| # | Decision |
|---|---|
| Strategy | Migrate existing catalog *and* enshrine the rule for new entries (option B from brainstorming). |
| Preserve originals | Yes — into `_archive/3mf-originals/<category>/<model-folder>/<name>.3mf` (option C: central dump, kept off the portal data volume). |
| Multi-body 3MF | Each object becomes its own STL (option B). Single-object stays unsuffixed; multi-object gets zero-padded suffix `_01`, `_02`, … |
| Folder naming for loose files | File basename, 1:1, preserving capitalization and spaces. |
| 3MF in folder that already has sibling STL | Archive without conversion (avoids duplicates). |
| `wlasne modele/mosfet_hw-700_case/` | Move to `narzedzia/mosfet_hw-700_case/`. Update index entry: `category: "tools"`, new `path`. |
| `wlasne modele/` (rest) | Delete `*.FCStd`, `*.FCBak`, `test_spiecia.3mf`. Remove the directory. Drop the two corresponding index entries. |
| Conversion validity | STL must have > 0 triangles and bbox > 0 on all 3 axes. Failure → 3MF stays in place; flagged in report. |
| Conversion library | `trimesh` 4.x with `[easy]` extras (validated empirically across small / medium / large multi-body 3MFs and a FreeCAD-origin file — all round-trip clean, face-count exact). Fallback if a 3MF refuses to load: OrcaSlicer Linux AppImage in `/mnt/d/orca_installers/`. |

## Architecture

### Code (3d-portal git repo)

- `infra/scripts/migrate-catalog-3mf.py` — single-file Python migration
  tool with `--dry-run` (default) and `--apply` modes, plus `--convert
  PATH/file.3mf` for single-file use during onboarding new models.
- `infra/scripts/requirements-migrate.txt` — pinned deps:
  `trimesh[easy]==4.12.2`, `numpy>=2,<3`. Kept separate from app
  dependencies; only loaded when this script runs.
- `infra/scripts/tests/test_migrate_3mf.py` — unit tests for converter
  and scanner/planner.
- `infra/scripts/sync-data.sh` — extended with `--exclude='_archive/'`.

### Rule documentation (catalog `AGENTS.md`)

- `Repository Structure` section gains `_archive/` entry.
- `File Types` table: `.3mf` row changes from "Do NOT unpack or modify"
  to "Convert to STL on entry, archive original to
  `_archive/3mf-originals/`".
- New section `3MF conversion workflow` describes:
  - Trigger (any 3MF arriving in the catalog).
  - Output (per-object STLs in the model folder).
  - Naming convention (single-object: `<basename>.stl`; multi-object:
    `<basename>_NN.stl`, zero-padded).
  - Original archival path.
- Categorization Rules table: `wlasne modele/` row removed.
- Enums: `category` enum loses `own_models`.
- `Workflow: Adding a New Model` step "Download the files immediately"
  expanded to include "If any downloaded file is `.3mf`, run the
  migrate-catalog-3mf converter on it before continuing."

### Migration artifact (3d-portal git repo)

- `docs/migration-reports/2026-05-02-3mf-to-stl-migration.md` — written
  by `--apply`. Audit trail with: per-file action (wrap / move /
  convert / archive / delete / index-edit), input/output sizes,
  triangle counts, validation outcomes, exit code, duration. Committed
  to git after the run.

## Components (script internals)

The script is one Python file (~400-600 LOC) with five logical units.

**1. Scanner.** Walks the catalog. Per top-level category:
- For each immediate child:
  - File at category root → emit `WrapInFolder(file, basename)`.
  - Directory → recurse, skipping the model's `prints/` subdirectory
    (image-only) and any `_archive/` directory if it ever appears
    inside a model folder. For every `*.3mf` found, emit
    `Archive3mf(path)` if a sibling `*.stl` / `*.STL` exists in the
    same directory, otherwise emit `Convert3mf(path) → Archive3mf(path)`.
- Special-case `wlasne modele/`:
  - `mosfet_hw-700_case/` → `MoveDir(src, narzedzia/mosfet_hw-700_case)`.
  - Anything else (`*.FCStd`, `*.FCBak`, `test_spiecia.3mf`) →
    `DeleteFile(path)`.
  - After all of the above → `RemoveEmptyDir(wlasne modele/)`.

**2. Planner.** Takes the action list plus the current `_index/index.json`.
Produces:
- A markdown plan (human-readable) listing every action and every
  affected index entry.
- Validations:
  - No collision: for each `WrapInFolder(file, basename)`, check that
    `<category>/<basename>/` does not already exist as a directory.
  - For each `Convert3mf(path)`, simulate the multi-body output names
    against the live filesystem to catch pre-existing collisions.
  - Each existing index entry's `path` must map to exactly one
    post-migration location.
- An explicit list of index entries to delete
  (`podstawka_laptop_latitude_5450.FCStd`, `test_spiecia.FCStd`).

**3. Converter.** `convert_3mf_to_stls(path: Path) -> list[Path]`.
- `trimesh.load(path)` → `Trimesh` or `Scene`.
- For Scene: iterate `scene.geometry.items()`. For Trimesh: wrap as
  `[("solo", mesh)]`.
- Per mesh: call `mesh.fix_normals()` (per AGENTS.md lessons learned).
  Validate: `len(mesh.faces) > 0` and `mesh.bounds` extent > 0 on x, y, z.
  Any failure aborts the conversion of this 3MF and unwinds any STL
  files written so far for it.
- Output naming:
  - Single object: `<basename>.stl`.
  - Multi-object: `<basename>_NN.stl`, zero-padded to `max(2,
    len(str(N_objects)))` digits, 1-indexed.
  - Lowercase `.stl` extension always.
- After write: round-trip read each STL via `trimesh.load`; assert face
  count matches the source mesh.

**4. Executor.** Runs actions in fixed order: wraps → mosfet move →
conversions → archives → wlasne-modele cleanup → index update. Each
action logs `before`/`after` paths and metadata into the report.

**5. IndexUpdater.** Rewrites `_index/index.json`:
- Update `path` for each entry whose target moved (wrapped or
  mosfet).
- Update `category` for the mosfet entry: `own_models` → `tools`.
- Drop the two FCStd-based entries.
- Preserve existing JSON formatting (verify by reading a sample of
  the existing file: indent width, trailing newline, key order).

## Data flow (`--apply`)

1. Parse CLI args. Default: `--dry-run`.
2. Sanity checks:
   - Catalog root exists and is readable.
   - `_index/index.json` parses as JSON (also produces backup at
     `_index/index.json.bak-<UTC-iso8601>`).
   - `python -c "import trimesh; import networkx; import lxml"`
     succeeds.
   - Best-effort warning for in-progress Nextcloud sync (heuristic:
     presence of `.~lock*` or `*.part` files in the catalog).
3. Scanner pass → action list.
4. Planner pass → markdown plan + validation. Plan goes to stdout in
   `--dry-run`, or to in-memory buffer that becomes part of the report
   in `--apply`.
5. (`--apply` only) Executor runs actions in order. Each action is
   wrapped in try/except; failures of independent actions (one 3MF's
   conversion) do not abort the whole run.
6. (`--apply` only) IndexUpdater writes the new `_index/index.json`.
7. Report markdown written to `docs/migration-reports/<UTC-date>-3mf-
   to-stl-migration.md`. Exit code reflects worst observed status:
   0 = clean, 1 = manual reviews pending, 2 = unrecoverable error.

After the script, the operator:
- Inspects 5–10 random output STLs in OrcaSlicer (sanity check).
- Updates the catalog `AGENTS.md` (separate from the script run; can
  be done by an agent reading this spec).
- Commits the script + report in `3d-portal`.
- Runs `./infra/scripts/sync-data.sh` to push to `.190` and refresh
  the portal index.

### Idempotency

Re-running `--apply` on a finished catalog produces an empty action
list (no loose files at category roots; no 3MFs outside `_archive/`;
all index `path`s match disk). Plan: zero ops. Exit 0. The
`*.bak-<timestamp>` of the index accumulates one per run; harmless.

## Error handling

| Scenario | Reaction |
|---|---|
| 3MF conversion fails (load error, invalid STL, 0 triangles) | 3MF stays put, no archive, no index path change. Report entry "manual review" with full traceback. Other 3MFs continue. Exit code ≥ 1. |
| Post-conversion STL invalid (0 triangles or 0 bbox) | Delete the orphan STL file. Treat as conversion failure for the parent 3MF. |
| Wrap collision (`<category>/<basename>/` already exists) | Abort wrap for this file. Report shows the conflict. |
| Convert output collision (a target STL name already exists) | Abort conversion for this 3MF. Report explains. |
| Index entry `path` no longer exists post-migration | Listed as orphan in the report. Not auto-deleted unless explicitly enumerated (`podstawka_laptop_latitude_5450.FCStd`, `test_spiecia.FCStd`). |
| `_index/index.json` parse error before any work | Abort, no modifications, exit 2. |
| trimesh / dependency missing | Print install command, abort, exit 2. |
| WSL2 readdir EINVAL | Wrap each `os.scandir` / `shutil.move` in try/except OSError. On EINVAL: retry once after `time.sleep(0.5)`; persistent failure → log path and continue. |
| Operator interrupt (SIGINT) | Finish the currently-in-flight conversion (atomic), then exit. The index is *not* yet written, so the next `--apply` resumes from the on-disk state. |
| `_archive/` does not exist | Created on demand (`mkdir -p`). |
| Permission denied (Orca / Bambu Studio holding a file open) | Fail with the offending path; suggest closing the slicer and retrying. |

The report has fixed sections: `## Wraps`, `## Conversions
(success)`, `## Conversions (failed — manual review)`, `## Archives`,
`## Index changes`, `## Warnings`, `## Errors`, `## Summary`. The
summary contains action counts, exit code, duration, and a single
"NEXT STEPS" list for the operator (e.g. "open these N 3MFs in
Orca to triage" if any conversions failed).

## Testing

**Tier 1 — Converter unit tests (pytest).**
- Fixtures generated in-memory by trimesh: a sphere, a cube+sphere
  scene, a degenerate (zero-triangle) mesh.
- Cover: single-object output naming, multi-object output naming,
  rejection of degenerate meshes, round-trip face-count match.

**Tier 2 — Scanner/Planner unit tests.**
- Synthetic catalog under `tmp_path`: a few loose files, a folder
  with 3MF+STL, a folder with only 3MF, a mocked `wlasne modele/`.
- Assert exact action list and post-migration index spec match
  expectations.

**Tier 3 — End-to-end on a partial catalog clone.**
- `cp -r` a subset of `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/`
  (decorum + praktyczne + wlasne modele + _index) into
  `/tmp/catalog-clone-<date>`. Run the script with `--catalog-root
  /tmp/...` `--apply`. Inspect 3-5 output STLs in OrcaSlicer via
  `\\wsl.localhost\...` UNC.

**Tier 4 — Real-catalog post-migration validation.**
- `find $ROOT -mindepth 2 -maxdepth 2 -type f \( -iname '*.stl' -o
  -iname '*.3mf' -o -iname '*.step' \)` → empty.
- `find $ROOT -path '*/_archive/*' -prune -o -iname '*.3mf' -print`
  → empty (modulo manual-review items called out in the report).
- Index parses, every `path` exists, count = `previous - 2`.

**Tier 5 — Portal smoke test.**
- After `sync-data.sh` pushes to `.190`, hit `POST /api/admin/refresh-
  catalog`. Open the portal UI, navigate to 2-3 affected models
  (mosfet, BunBowl, Stria Paper Holder). ModelViewer must render the
  geometry.

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| trimesh fails on an exotic 3MF (unusual encoding, unsupported feature) | Low — empirical sample of 5 across categories all passed | Conversion failure flagged for manual review; original 3MF preserved. Operator can fall back to OrcaSlicer (Linux AppImage in `/mnt/d/orca_installers/`) for one-off conversions. |
| Multi-body 3MF object names collide across two 3MFs in the same folder | Very low — naming is prefixed by 3MF basename | Planner detects pre-existing collisions; aborts that conversion. |
| Nextcloud sync conflicts during `--apply` | Medium — Nextcloud is active during weekdays | Operator runs sync, waits for green status, then runs `--apply`. Script warns on `*.part` / `.~lock*` presence. |
| `_index/index.json` schema drift between catalog clones | Low — single source of truth | Script reads the live file once, mutates in memory, writes back; operator-driven schema changes go through a separate workflow. |
| STEP files in `narzedzia/stealth_press_12/` accidentally touched | None — script only handles `*.3mf` and explicitly enumerated extensions for the wrap step | Scanner ignores `*.step`/`*.stp` entirely except for log purposes. |
| Disk pressure on Nextcloud due to STL inflation (e.g. Crab.3mf 12 MB → 41 MB STL) | Medium — total inflation likely < 1 GB across the catalog | Acceptable; archived 3MFs roughly offset by being moved into `_archive/` (still synced by Nextcloud, but excluded from portal volume). |

## AGENTS.md (catalog) edits — concrete diff sketch

In `/mnt/c/Users/ezope/Nextcloud/3d_modelowanie/AGENTS.md`:

1. `Repository Structure` block: add a line for `_archive/` between
   `_index/` and `AGENTS.md`. One-line description: "Archived
   originals (3MF source files post-conversion). Excluded from the
   portal data volume."
2. `File Types` table: rewrite the `.3mf` row.
   - From: `Bambu Studio / Creality Print project (settings + mesh) | Do NOT unpack or modify — these are slicer files.`
   - To: `Bambu Studio / Creality Print project (settings + mesh) | Convert to STL on entry, archive original to _archive/3mf-originals/. See "3MF conversion workflow".`
3. `Repository Structure` block: drop the `wlasne modele/` line.
4. `### Folder naming` subsection: drop the bullet "Own work:
   snake_case in Polish (no diacritics), e.g. `obudowa_czujnika`."
   (no `wlasne modele/` to put own work into anymore).
5. `Enums.category` table: drop the `own_models` row.
5. `Workflow: Adding a New Model`, step 5 "Download the files
   immediately": add a bullet point: "If any downloaded file is `.3mf`,
   run `migrate-catalog-3mf.py --convert <path>` against it before
   continuing — this writes per-object STLs into the model folder and
   archives the original."
6. New section after `Workflow: Status Updates`, titled `3MF Conversion
   Workflow`. Documents trigger, output paths, naming, validation, and
   the failure mode (3MF stays put, manual review).

## Open questions / non-decisions

None at design time. All clarifications resolved during brainstorming.
The implementation plan (next step) will surface any details that
turn out to need a decision during build.

## Next step

Hand off to the `superpowers:writing-plans` skill, which will produce
the implementation plan referencing this spec.
