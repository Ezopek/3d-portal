# Catalog card image carousel — design

**Status:** Draft, awaiting user review.
**Date:** 2026-05-01.
**Owner:** Michał (single-developer repo).
**Related code:** `apps/web/src/ui/custom/ModelCard.tsx`, `apps/web/src/modules/catalog/routes/CatalogList.tsx`, `apps/web/src/modules/catalog/routes/CatalogDetail.tsx`, `apps/api/app/modules/catalog/files.py`, `apps/api/app/modules/catalog/models.py`.

## 1. Goal

Let users skim a model's photos directly from the catalog grid, without navigating into the detail view. Each card becomes a lightweight image carousel with arrow controls and a dot indicator. Optimised for users on cellular/wifi reaching the portal externally — every byte that isn't strictly needed for the visible image is deferred.

## 2. Non-goals

- Fullscreen lightbox on the card (still belongs to the detail view).
- Image editing, reordering, or admin "set thumbnail" controls on the card (admin uses the detail Gallery, unchanged).
- Server-side image optimisation pipeline beyond on-demand thumbnail resize (no bg pre-generation worker).
- Carousel for the share view (`ShareView`) — out of scope for this iteration; can be revisited separately.

## 3. UX summary

**Default state:** card looks like today — single thumbnail (`thumbnail_url`), title, badges. If `image_count >= 2`, a row of dots appears subtly overlaid at the bottom of the image area.

**Interaction trigger (hybrid pattern):**
- Dots are visible **always** when there is more than one image — that is the persistent hint "there's more here". Tapping a dot jumps to that index.
- **Desktop:** left/right arrow buttons appear on hover, overlaid on the image edges with a translucent background. Click on the card area outside the arrows/dots navigates to the detail view (current behaviour preserved).
- **Mobile / touch:** arrows are hidden (no reliable hover); horizontal **swipe** on the image area is the primary nav. Tap on the image area (without swiping) still navigates to detail. Dots remain tappable and provide the visible affordance that there is more to see.

Detection of "touch device" is via `(hover: hover) and (pointer: fine)` media query — purely CSS, no JS state needed for the arrow visibility split.

**Loading transition:** when the user requests the next image, the current `<img>` gets a subtle CSS blur (e.g. `filter: blur(4px)` with a short transition), the next image loads in the background, and the blur is removed when `onLoad` fires. No spinner.

**Dot rendering:** if `image_count <= 7` show one dot per image. If `image_count > 7`, show 7 dots with the active one tracking position and a "+N" counter beside the dots (or similar — exact compact pattern is an implementation detail to iterate on during the visual regression pass, since 7 dots may itself look crowded on a small card).

**Edge cases:**
- `image_count <= 1` → no dots, no arrows, behaves exactly like today.
- Image fails to load (`onError`) → skip to next available; if all images in the list have failed, fall back to the original `thumbnail_url` and hide arrows/dots.
- Card width too narrow (e.g. 2-column mobile breakpoint) → still render dots, but arrows can be collapsed to slightly larger tap targets.

## 4. Architecture

The change touches three layers:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ apps/api                                                                 │
│  ├─ catalog/service.py     +image_count per model (cheap to compute)     │
│  ├─ catalog/models.py      +image_count: int on ModelListItem            │
│  └─ catalog/files.py       +?w=N query param → on-the-fly resize         │
│                            +filesystem thumbnail cache (data/cache/...)  │
└──────────────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ HTTP
                                 │
┌──────────────────────────────────────────────────────────────────────────┐
│ apps/web                                                                 │
│  ├─ lib/galleryCandidates.ts (new)  ← pure function moved out of         │
│  │                                    CatalogDetail; lists image URLs    │
│  │                                    from a Model + files response      │
│  ├─ modules/catalog/hooks/useGallery.ts (new) ← lazy React Query hook    │
│  ├─ ui/custom/CardCarousel.tsx (new) ← arrows, dots, blur transition     │
│  └─ ui/custom/ModelCard.tsx (modified) ← uses CardCarousel when          │
│                                          image_count >= 2                │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Backend — `image_count` on the list

`ModelListItem` gains `image_count: int`. Computed in `service.py` next to where `thumbnail_url` is resolved. Cheap inputs:

- `len([f for f in os.listdir(images_dir) if ext in IMAGE_EXTS])` — one `listdir`.
- `len(model.prints)` — already in memory.
- `+4` if `iso.png` exists in the renders dir for that model (one `stat`). The render worker generates the four views atomically, so trusting `iso.png` as a sentinel for the full set is safe enough; if a single view is missing the carousel will skip it via `onError` on the frontend.

Total per model: 1 `listdir` + 1 `stat`. For ~90 models that is ~90 `listdir` + ~90 `stat` per `/catalog/models` request, on a local NVMe — well under 100 ms even uncached. If profiling shows this is hot, later memoise per `(model_id, mtime)` in Redis. Not required for v1.

### 4.2 Backend — on-the-fly resize

`/api/files/{model_id}/{relative}` accepts an optional query param `w: int | None`. When `w` is set and the resolved file is an image (extension in {png, jpg, jpeg, webp}):

1. Compute cache key: `cache_dir / sha1(absolute_path).hexdigest()[:16]_{w}_{mtime_ns}.webp`.
   - Including `mtime_ns` makes the key self-invalidating: when the source file changes, the key changes and a new variant is generated. Stale orphaned entries can be pruned by `rm -rf cache/thumbnails` whenever; they regenerate on demand.
2. If cache file exists → serve it via `FileResponse`. Add `Cache-Control: public, max-age=86400` (1 day) and ETag.
3. If not → load via Pillow, `image.thumbnail((w, w))` preserving aspect, save as WebP at quality 80, write to cache file, then serve.

Width allowlist: `{240, 480, 720, 960, 1280}` to cap variants. Requests outside the allowlist get 400 — prevents an attacker generating 10 000 cache entries by enumerating widths. Frontend uses `?w=480` and `?w=960` (1x and 2x for cards) and `?w=1280` for the detail page.

For non-image files or `w` not provided, the endpoint serves the file unchanged (current behaviour, current `Cache-Control: private, max-age=300`).

Pillow is added as a backend dependency (`pillow>=10.4` in `apps/api/pyproject.toml`).

Cache dir resolution: `settings.cache_dir = Path("/data/cache/thumbnails")` (or env-driven via `CATALOG_CACHE_DIR`), created on app startup. Volume-mounted in compose so it survives container restarts; mount target picked alongside the existing `renders_dir` mount.

### 4.3 Frontend — `lib/galleryCandidates.ts`

Pure function extracted from `CatalogDetail.tsx`:

```ts
export function pickGalleryCandidates(
  model: { id: string; path: string; prints: Print[] },
  files: string[],
): GalleryImage[]
```

Returns ordered, deduped list: `images/*.{png,jpg,webp}` → prints (sorted desc by date) → `iso/front/side/top.png`. Used both by the existing detail page (refactored to call this helper) and by the new lazy hook.

### 4.4 Frontend — `useGallery(modelId)` hook

Thin wrapper around React Query:

```ts
useQuery({
  queryKey: ["catalog", "gallery", modelId],
  queryFn: () => api(`/catalog/models/${modelId}/files`).then(r => pickGalleryCandidates(model, r.files)),
  enabled: false,  // manual; called by CardCarousel on first interaction
  staleTime: 5 * 60 * 1000,
})
```

`enabled: false` means it won't fire on mount. `CardCarousel` calls `refetch()` (or the React Query `useQuery` `enabled` flips to `true` on first interaction). React Query caches per `modelId`; navigating into the detail and back re-uses the same cache.

### 4.5 Frontend — `CardCarousel.tsx`

Props:

```ts
interface Props {
  modelId: string
  initialThumbnailUrl: string | null  // model.thumbnail_url
  imageCount: number                   // from list
  alt: string
}
```

Internal state:
- `index: number` (0 = initial thumbnail).
- `loadedUrls: string[]` — populated lazily after `useGallery` resolves.
- `isTransitioning: boolean` — drives the blur class.

Behaviour:
- Renders a single `<img>` that shows `loadedUrls[index] ?? initialThumbnailUrl`, with `srcSet="...?w=480 1x, ...?w=960 2x"`.
- Renders dot indicator overlay (`absolute bottom-2 inset-x-0`), rendering up to 7 dots + counter.
- On hover (CSS-only via group-hover) shows arrow buttons `absolute inset-y-0 left/right-1`.
- On arrow click or swipe (using `react-swipeable` or a hand-rolled touchstart/end pair — to be picked at implementation): if `useGallery` hasn't fetched yet, `refetch()`; once URLs are available, advance `index`, set `isTransitioning: true`, swap `src`, await `onLoad`, clear `isTransitioning`.
- Arrow click `stopPropagation()` so the surrounding `<Link>` to the detail page doesn't fire.
- Dots tappable → jump to that index (same fetch-then-load flow).

### 4.6 Frontend — `ModelCard.tsx` change

Replace the inline `<img>` block with:

```tsx
{model.image_count >= 2 ? (
  <CardCarousel
    modelId={model.id}
    initialThumbnailUrl={model.thumbnail_url}
    imageCount={model.image_count}
    alt={primary}
  />
) : (
  /* existing single-image render */
)}
```

The card itself remains a `<Link>` to `/catalog/$id`; carousel arrow/dot clicks `stopPropagation()` so they don't trigger navigation.

## 5. Data flow

Initial render of `/catalog`:
1. `GET /api/catalog/models` → list with `thumbnail_url` and `image_count` per model.
2. Each card renders `thumbnail_url` (one HTTP image request per card via `?w=480/960`).
3. Cards with `image_count >= 2` show dots immediately, no extra requests.

User clicks `→` on card X for the first time:
1. `useGallery(X)` triggers `GET /api/catalog/models/X/files` (small JSON).
2. `pickGalleryCandidates(model, files)` produces ordered URL list.
3. Carousel sets `index = 1`, blur applied, loads `urls[1]?w=480/960`.
4. `onLoad` removes blur. Browser caches the image (HTTP `Cache-Control` from API).

User clicks `→` again:
1. URL list already in React Query cache.
2. Carousel advances `index`, blur applied, loads `urls[2]`.
3. Subsequent revisits to card X (within `staleTime` 5 min) skip the JSON refetch entirely; image bytes come from browser HTTP cache.

User navigates into detail view and back:
1. URL list cached → no refetch.
2. Card thumbnails reload from browser cache.

## 6. API contract changes

### `ModelListItem` — adds field

```diff
 class ModelListItem(BaseModel):
     id: str
     ...
     thumbnail_url: str | None
     has_3d: bool
     date_added: str
+    image_count: int  # number of viewable images (catalog images + prints + 4 if renders exist), used by the card carousel to render dots
```

Frontend `apps/web/src/modules/catalog/types.ts` mirrors this addition.

### `/api/files/{id}/{relative}` — adds query param

```
GET /api/files/{id}/{relative}?w=480
```

- `w` ∈ {240, 480, 720, 960, 1280}, optional.
- Applies only to image extensions ({png, jpg, jpeg, webp}). For other types, ignored (current behaviour).
- Output Content-Type: `image/webp` when resized, original mime when not.
- Cache headers when resized: `Cache-Control: public, max-age=86400` + ETag.
- Invalid `w` → 400.

## 7. Testing

### Backend

- Unit test in `apps/api/tests/`:
  - `image_count` is computed correctly for: model with only `images/`, model with only prints, model with no extra images but renders, model with all three sources, model with nothing.
  - Resize endpoint: returns WebP for image with valid `w`, returns 400 for invalid `w`, ignores `w` for non-image, regenerates when source `mtime` changes (cache key invalidates).
  - ETag round-trip still works with resized variants.

### Frontend

- Unit test for `pickGalleryCandidates` (pure function, easy to cover):
  - dedupes correctly, preserves source priority order, handles empty inputs.
- Playwright visual regression in `apps/web/tests/visual/`:
  - Catalog list with at least one model that has `image_count >= 2` (dots visible, arrows hidden by default).
  - Same model, hover state (arrows visible).
  - Same model, after clicking next (image swapped, dot index advanced).
  - Model with `image_count <= 1` (legacy look unchanged).
- A Playwright behavioural test exercising the lazy fetch + blur transition (mocking the `/files` JSON, asserting blur class toggles on/off across `onLoad`).

## 8. Open implementation choices (deferred to writing-plans)

- Swipe library vs hand-rolled touch handlers in `CardCarousel`.
- Exact blur amount and transition duration (likely `blur(4px)` over `120ms`).
- Whether to render the dot overlay with `mix-blend-mode` or a translucent rounded pill background — picked during visual regression pass.
- Compact dot pattern when `image_count > 7` (7 dots + "+N", or 5 dots with counter, or a slim progress bar). Decide visually.

These are deliberately not pinned here — they are aesthetic details best decided with the actual rendered card in front of you, not in prose.

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Pillow added to the API container — slightly larger image, more CPU on first request per variant. | Variants are tiny (a few KB), generated once per `(path, mtime, w)`. Restricted width allowlist caps total variants. |
| `?w=N` cache directory grows unbounded over time as catalog churns. | Self-evicting via `mtime` in cache key for *current* files; orphaned entries from deleted/replaced files accumulate but are cheap to purge manually (`rm -rf cache/thumbnails`). Cleanup script can be added later if needed. |
| Network variability — first carousel interaction over slow cellular has visible lag. | Blur transition is intentionally subtle and forgiving. Once an image loads it's browser-cached, so subsequent navigation is instant. |
| Carousel arrows accidentally trigger `<Link>` navigation. | `stopPropagation()` on arrow/dot click handlers; covered by Playwright behavioural test. |
| `image_count` from the list could disagree with what the lazy fetch resolves (race if a sync runs between calls). | Carousel reconciles to the actual fetched list once available; dot count snaps to the real list. UX cost: dots may shrink/grow once on first interaction in this rare case. |

## 10. Deployment notes

- API image rebuild adds Pillow (~5 MB to image).
- New volume mount for thumbnail cache (`/data/cache/thumbnails`).
- After merge to `main`, run `infra/scripts/deploy.sh` to push to `.190`.
- No DB migration. No frontend lockfile churn beyond optional swipe dependency.
