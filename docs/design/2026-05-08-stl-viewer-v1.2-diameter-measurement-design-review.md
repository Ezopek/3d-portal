# STL Viewer v1.2 Diameter Measurement - Design Review

**Date:** 2026-05-08
**Reviewer:** Codex
**Reviewed document:** `docs/design/2026-05-08-stl-viewer-v1.2-diameter-measurement-design.md`
**Related context:** `docs/design/2026-05-06-stl-viewer-design.md`,
`docs/design/2026-05-07-stl-viewer-v1.1-plane-measurement-design.md`,
`docs/design/2026-05-07-stl-viewer-v1.1-plane-measurement-design-review.md`,
current `viewer3d/` implementation

## Verdict

The design is directionally good. Rim-based diameter measurement is a better v1
choice than full 3D cylinder fitting, and the preview-before-commit interaction
matches how inspection tools should feel: the viewer shows what it understood
before storing a measurement. The per-measurement palette and summary swatches
are also the right UX move now that measurements can coexist.

It is not implementation-plan-ready yet. The main gaps are around geometry
classification, lifetime of welded data, hover/click races, and a few UI details
that can make the feature feel unreliable even if the math is mostly correct.

Recommended decision before planning: **revise the design, then plan**.

## Findings

### P1 - Vertex-only circle fit can accept non-circular loops as diameters

The spec validates a rim by fitting a circle to loop vertices and checking
vertex radial residual. That is not enough to distinguish a circular STL rim
from many ordinary sharp loops.

The clearest example is already implicit in the proposed tests: starting on a
cube edge can produce a square loop around one face. The four square corners are
perfectly co-circular, so a vertex-only circle fit can report a valid diameter
for a cube face diagonal. Rectangles and many regular polygonal loops have the
same problem. This would make Diameter mode feel magical in the bad way: hover a
plain box edge and get a bogus `Ø` value.

The design should add a second roundness check, for example:

- include edge-midpoint residual or chord sagitta, not only vertex residual,
- reject loops with too few segments unless explicitly treated as approximate,
- limit max angular gap between consecutive loop vertices,
- optionally validate that adjacent side-face normals look radial around the
  fitted center.

This also needs a clear product decision for low-segment holes. The current text
says a 6-segment hex hole may be accepted as weak, but with vertex-only residual
it can fit exactly and will not be weak. With midpoint/sagitta validation, it
probably should be weak or rejected depending on the intended UX.

### P1 - Completed diameter measurements are too dependent on live welded data

`Rim.loopVertices` stores welded vertex indices. Rendering the completed rim
therefore still needs `welded.positions`. The spec says `needsWelding` includes
Diameter mode, but it does not say welding remains alive after the user leaves
Diameter mode while completed diameter measurements are still visible.

That creates a data-lifetime hole. If prep is keyed only by current mode, a
completed diameter measurement can lose the data needed to render its rim after
mode changes, cache release, or future refactors. The current v1.1 plane overlay
path has a similar risk because completed cluster overlays are also guarded by
`prep.welded !== null`.

The design should choose one of these contracts:

- store completed diameter loop points directly in the measurement, so the rim
  overlay is self-contained, or
- keep welded prep alive while any active or completed measurement needs welded
  coordinates, not only while the current mode needs picking.

For v1.2, storing loop points is probably the simpler and more robust option.
It also makes screenshots and future persistence easier.

### P1 - Click commit depends on asynchronous hover state

The flow says hover detection is `requestAnimationFrame` throttled and click
commits only if `hoveredRim !== null`. That can silently miss valid clicks:

- the user clicks just before the rAF hover computation finishes,
- the cursor enters the mesh and clicks before a pointermove preview settles,
- `hoveredRim` belongs to an older geometry/edge unless identity is tracked,
- the preview was cleared by a tiny pointer movement but the click event still
  contains a valid face and hit point.

For an inspection tool, a valid click on a visible rim should not fail because
the preview pipeline is one frame behind. The click handler should either run
the same detection synchronously from the click event, or commit only a preview
that is explicitly keyed by current `geometry.uuid`, source face, welded
triangle, and sharp edge key.

### P1 - The sharp-edge graph contract is under-specified

Loop walking needs fast "sharp edges incident to this welded vertex" lookup. The
spec describes this conceptually, but `WeldedMesh` currently only has triangle
indices and triangle adjacency. If each hover walk has to rediscover incident
edges by scanning triangles, the performance budget collapses.

The design should define a real `SharpEdgeGraph` cache built once per welded
mesh:

- one canonical key per welded edge,
- edge endpoint vertex ids,
- adjacent triangle ids or boundary/non-manifold metadata,
- per-vertex incident sharp edge ids,
- optional dihedral angle per edge,
- deterministic rejection of non-manifold edges instead of relying on the
  current one-neighbor adjacency model.

There is also a concrete typo: §4.1 says `dihedralAngles` has length
`welded.adjacency.length / 3`, but the sample implementation allocates
`triCount * 3`. One entry per triangle edge means the length should match
`welded.adjacency.length`, or the design should move to one entry per canonical
edge.

### P1 - Raycast and coordinate mapping need to be normative

The data flow says `raycast -> (triangleIndex, hitPoint)` and then uses that
triangle against welded data. In the implementation, raycast `faceIndex` belongs
to the displayed STL geometry and must be mapped through `sourceToWelded`.

The spec should explicitly require:

- `sourceFaceIndex -> weldedTriangleId` mapping before any diameter detection,
- `BOUNDARY`/degenerate source triangles to be skipped,
- local/world coordinate handling for `hitPoint` before distance-to-edge math.

The current mesh is not transformed, so local/world happen to align today. That
is a fragile implicit invariant for a geometry algorithm.

### P2 - First-hover performance claims hide main-thread work

Welding already has a worker path, but the new sharp-edge classification, edge
graph construction, and maybe circle-fit cache are introduced as lazy work on
first Diameter use. The table claims `computeSharpEdges` costs about 10 ms for
500k triangles, but that number is optimistic unless the graph is carefully
implemented and likely moved into the same preparation phase.

Better UX would be:

- Diameter enters a "Preparing circular edges..." state while welding and sharp
  edge graph preparation run,
- heavy prep is cancellable through the existing Esc ladder,
- hover only does cheap lookup plus cached loop/fit checks,
- loop/fit results are memoized by canonical sharp edge key.

If this remains first-hover work on the main thread, the first interaction with
a large STL can feel like the viewer froze.

### P2 - Silent failure UX is too quiet for imperfect meshes

Using "no preview" as the primary signal is good while hovering. Making a click
without preview a silent no-op is harsher. Users will click near a rim and get
nothing, with no way to tell whether they missed, welding is not ready, the loop
is non-circular, the mesh is broken, or the algorithm is too strict.

Recommended revision: keep hover failures quiet, but after an explicit click in
Diameter mode with no valid rim, show a short non-modal message such as "No
circular rim detected here" with rate limiting. This is especially important
because real catalog STLs will include low-quality meshes.

### P2 - Diameter copy still leaks the plane-selection mental model

Diameter reuses v1.1 welding UX, but some copy remains plane-specific:

- `viewer3d.measure.step.preparing` currently says "Preparing planes...",
- `viewer3d.welding_failed` says mesh analysis failed for plane selection,
- the design lists a Diameter step key but not a Diameter-specific preparing
  or error string.

This should become generic mesh-analysis copy or have mode-specific strings.
Otherwise Diameter mode will feel bolted onto the plane tool instead of being a
first-class measurement mode.

### P2 - Palette E needs contrast and accessibility gates

The palette direction is good, but the current constants need visual acceptance
criteria. `sel2` uses the same hue with lower lightness (`L = 0.50`). On the
always-dark viewer canvas, some hues may be too subdued, especially for thin
lines and transparent plane overlays.

The design should define:

- minimum perceived contrast for rim/line overlays against the dark canvas,
- swatch outlines so light swatches remain visible on cards,
- behavior for colorblind users beyond hue rotation: numbers, labels, and maybe
  subtle stroke/dash differences if colors get close,
- how `Three.Color` values are converted back to CSS swatch colors without
  accidentally using linear RGB as display RGB.

The MeasureSummary legend is a strong idea; it deserves a concrete contrast QA
gate.

### P2 - Hiding the tolerance popover can create toolbar layout shift

The spec hides the tolerance popover in `off`, `p2p`, and `diameter`. That saves
space, but it can also move toolbar buttons when the user changes modes. In a
compact canvas toolbar, controls should not jump under the cursor.

If the tolerance control is hidden, reserve a stable slot or define a responsive
measurement menu. If the slot is not reserved, keep the control visible but
disabled outside plane modes. Either decision can work; the spec should choose
one intentionally.

### P2 - Label placement is not robust enough for orbiting

The label position is `rim.center + tangent * (radius + 4mm)`, with tangent
chosen near the camera direction at first render and only recomputed on
`resetSignal`. That avoids twitch, but it can leave labels behind the model,
inside visual clutter, or overlapping other labels after orbiting.

The design should define a screen-aware placement rule, or at least a hysteresis
rule that can move the label when it becomes unreadable. It should also specify
depth behavior for rim lines and labels: whether they respect occlusion, render
on top, or use a subtle offset to avoid z-fighting on the mesh edge.

### P2 - Keyboard shortcut behavior needs focus rules

`D` as the Diameter shortcut is sensible, but the current key handling only
covers Esc and file navigation. The design should specify where the shortcut is
registered and when it is ignored:

- ignore when the file selector search, tolerance input, or any text input has
  focus,
- work in both modal and inline viewer when the viewer has focus,
- preserve Dialog keyboard behavior,
- expose the same accessible label/tooltip copy without relying on hover.

This is small, but it prevents shortcut regressions and accidental mode changes.

### P2 - The color index rule has an off-by-one inconsistency

Most of the spec correctly says the next measurement uses
`paletteFor(state.completed.length, slot)`. §6.3 says hover renders with
`paletteFor(N+1, "sel1")`. If `N` means current completed count, that is an
off-by-one error. If `N` means the next human-visible number, the text should say
that explicitly.

Make the zero-based rule normative in one place and use human labels only for
display.

### P2 - Test expectations conflict with desired behavior

Several proposed tests encode the current ambiguities:

- `sharpEdges.test.ts` says a 32-segment plate hole has "32 hole-rim sharp
  edges (top + bottom)", while an earlier table says `2N + 12`. Top and bottom
  rims for a 32-segment hole should not both total 32.
- `loopWalk.test.ts` expects a cube edge to return a square loop. That is fine
  as a loop-walker unit test, but the full detector must reject it as a
  diameter unless square bosses are intentionally measurable.
- `circleFit.test.ts` should include square, rectangle, regular hexagon, and
  edge-midpoint/sagitta cases, not only ellipse and collinear cases.
- The visual hover tests will be coordinate-sensitive in WebGL. The fixture and
  helper should choose camera framing and click/hover points that are stable
  across Chromium updates.

The test plan is close, but it should test the product-level detector, not only
each happy-path helper.

### P3 - File and token naming drift will create implementation churn

The design says to keep `--color-viewer-paint`, but the current token is
`--color-viewer-mesh-paint`. It also introduces `apps/web/tests/unit/*`, while
most viewer unit tests currently live next to the implementation under
`viewer3d/measure` or `viewer3d/lib`.

These are not product risks, but cleaning them up before planning will reduce
small avoidable diffs.

### P3 - Color renumbering on delete is real UX debt

The spec accepts color changes after deleting a measurement. That may be fine
for v1.2, but the wording underplays the user impact. The whole point of the
palette is that users can map a row to a 3D overlay. Recoloring every later
measurement after deleting `#2` breaks that mapping at exactly the moment the
user is managing multiple measurements.

If stable `colorIndex` is still deferred, call it out as deliberate UX debt and
include it in manual smoke testing. If it feels bad during smoke, storing
`colorIndex` on `Measurement` is likely worth the small type cost.

## What Looks Good

- Rim-first measurement is the right v1.2 scope. It avoids brittle cylinder
  fitting and works for thin-sheet holes where the meaningful target is the rim.
- Single-click commit after hover preview is a good interaction model. It keeps
  Diameter simpler than the two-step plane modes.
- Retrofitting color to all measurement kinds is the right time to do it; a
  diameter-only color system would fragment the viewer.
- MeasureSummary swatches are a strong UX choice because they turn the panel
  into a legend instead of just a list of numbers.
- Keeping the backend untouched is appropriate for a viewer-only measurement
  feature.
- The v2 roadmap is correctly separated. Auto-detect picking and cross-type
  measurement belong in their own rewrite, not hidden inside this slice.

## Suggested Design Revisions

Before writing the implementation plan, tighten these decisions:

1. Define a product-level diameter detector, not just `walkEdgeLoop` plus
   vertex circle fit. Include false-positive cases such as cube faces,
   rectangles, square bosses, hex holes, and filleted rims.
2. Decide whether completed diameter measurements store loop points or keep
   welded data alive. Make the same decision explicit for completed plane
   overlays if needed.
3. Introduce a cached `SharpEdgeGraph` with vertex incidence and canonical edge
   ids. Avoid per-hover graph discovery.
4. Make click handling robust by recomputing from the click event or validating
   that the hover result matches the current geometry and edge.
5. Replace plane-specific loading/error copy with mode-aware mesh-analysis copy.
6. Add palette contrast and swatch conversion rules, then test several
   measurement counts on the dark viewer canvas.
7. Pick a stable toolbar behavior for the tolerance control so mode changes do
   not shift nearby buttons.
8. Align tests with the intended user behavior, especially false positives and
   low-segment circular features.
