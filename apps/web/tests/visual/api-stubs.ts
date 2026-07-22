import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { Page, Route } from "@playwright/test";

import type { TagGroupsResponse, TagListItem } from "@/lib/api-types";

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Intercept the STL content endpoint for a specific {modelId, fileId} and
 * serve a deterministic 12-triangle cube fixture so the WebGL render is
 * stable across machines (within Playwright's pixel-ratio tolerance).
 */
export async function stubViewerStl(
  page: Page,
  modelId: string,
  fileId: string,
) {
  const cube = readFileSync(join(__dirname, "fixtures", "cube.stl"));
  await page.route(
    `**/api/models/${modelId}/files/${fileId}/content**`,
    (route: Route) =>
      route.fulfill({
        status: 200,
        contentType: "model/stl",
        body: cube,
      }),
  );
}

/**
 * Stub the SoT model-detail endpoint with one STL file and one image file,
 * tailored for the viewer3d visual regression suite. `withThumbnail`
 * controls whether the inline pane shows the offline-render placeholder
 * (true) or auto-loads the STL into the canvas (false).
 */
export async function stubViewerModelDetail(
  page: Page,
  opts: { modelId: string; stlFileId: string; thumbnailFileId?: string | null },
) {
  const { modelId, stlFileId } = opts;
  const thumb = opts.thumbnailFileId ?? null;
  await page.route(`**/api/models/${modelId}`, (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: modelId,
        slug: "cube",
        name_en: "Cube",
        name_pl: "Sześcian",
        category_id: "c1",
        source: "own",
        status: "not_printed",
        rating: null,
        thumbnail_file_id: thumb,
        date_added: "2026-05-06",
        deleted_at: null,
        created_at: "2026-05-06T00:00:00Z",
        updated_at: "2026-05-06T00:00:00Z",
        tags: [],
        gallery_file_ids: [],
        image_count: 0,
        category: {
          id: "c1",
          parent_id: null,
          slug: "tools",
          name_en: "Tools",
          name_pl: "Narzędzia",
        },
        files: [
          {
            id: stlFileId,
            model_id: modelId,
            kind: "stl",
            original_name: "cube.stl",
            storage_path: "",
            sha256: "",
            size_bytes: 684,
            mime_type: "model/stl",
            position: 1,
            selected_for_render: true,
            created_at: "2026-05-06T00:00:00Z",
          },
          {
            id: "thumb-1",
            model_id: modelId,
            kind: "image",
            original_name: "iso.png",
            storage_path: "",
            sha256: "",
            size_bytes: 1024,
            mime_type: "image/png",
            position: 2,
            selected_for_render: false,
            created_at: "2026-05-06T00:00:00Z",
          },
        ],
        prints: [],
        notes: [],
        external_links: [],
      }),
    }),
  );
  // Generic image fallback (thumbnail PNG, gallery, etc.).
  await page.route("**/api/models/**/files/**/content**", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "base64",
      ),
    }),
  );
}

// Default `/api/tags*` fixture for `stubSotList` — 2 flat tags. Extracted to a
// module-level constant (E47 47.2 consolidation, NFR25-VISUAL-1) so callers
// needing a richer fixture (more tags, real UUID ids) can override it via
// `stubSotList`'s `opts.tags` without registering a duplicate route handler.
// Deliberately NOT annotated `: TagListItem[]` — these fixture rows predate
// the `group_id`/`group_position` facet fields on `TagRead` and adding them
// here would change the JSON body served to the 18 existing zero-arg call
// sites (byte-for-byte behavior-preserving requirement, spec-47-2).
const DEFAULT_TAGS = [
  { id: "tag-1", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
  {
    id: "tag-2",
    slug: "articulated",
    name_en: "Articulated",
    name_pl: null,
  },
];

// Default `/api/tag-groups*` fixture for `stubSotList` — 1 group ("theme"),
// empty groupless. Extracted alongside `DEFAULT_TAGS` for the same reason;
// see its comment above (also deliberately unannotated for the same reason).
const DEFAULT_TAG_GROUPS = {
  groups: [
    {
      id: "33333333-3333-3333-3333-333333333333",
      slug: "theme",
      name_en: "Theme",
      name_pl: "Motyw",
      position: 0,
      tags: [
        {
          id: "tag-1",
          slug: "dragon",
          name_en: "Dragon",
          name_pl: "Smok",
          model_count: 1,
        },
        {
          id: "tag-2",
          slug: "articulated",
          name_en: "Articulated",
          name_pl: null,
          model_count: 0,
        },
      ],
    },
  ],
  groupless: [],
};

export async function stubSotList(
  page: Page,
  opts: { tags?: TagListItem[]; tagGroups?: TagGroupsResponse } = {},
) {
  const tags = opts.tags ?? DEFAULT_TAGS;
  const tagGroups = opts.tagGroups ?? DEFAULT_TAG_GROUPS;
  await page.route("**/api/categories", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        roots: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            parent_id: null,
            slug: "decorations",
            name_en: "Decorations",
            name_pl: "Dekoracje",
            children: [
              {
                id: "11111111-1111-1111-1111-111111111112",
                parent_id: "11111111-1111-1111-1111-111111111111",
                slug: "vases",
                name_en: "Vases",
                name_pl: "Wazony",
                children: [],
                model_count: 1,
              },
            ],
            model_count: 1,
          },
          {
            id: "22222222-2222-2222-2222-222222222222",
            parent_id: null,
            slug: "tools",
            name_en: "Tools",
            name_pl: "Narzędzia",
            children: [],
            model_count: 1,
          },
        ],
      }),
    }),
  );

  await page.route("**/api/tags*", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(tags),
    }),
  );

  // CatalogList started consuming this endpoint in E44.3. Keep its response
  // shape alongside the list fixtures; without it every catalog visual test
  // falls into the network-error state.
  await page.route("**/api/tag-groups*", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(tagGroups),
    }),
  );

  await page.route("**/api/models*", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 2,
        offset: 0,
        limit: 48,
        items: [
          {
            id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            slug: "dragon",
            name_en: "Dragon",
            name_pl: "Smok",
            category_id: "11111111-1111-1111-1111-111111111111",
            source: "printables",
            status: "printed",
            rating: 5,
            thumbnail_file_id: "f1111111-1111-1111-1111-111111111111",
            date_added: "2026-04-12",
            deleted_at: null,
            created_at: "2026-04-12T00:00:00Z",
            updated_at: "2026-04-12T00:00:00Z",
            tags: [
              {
                id: "tag-1",
                slug: "dragon",
                name_en: "Dragon",
                name_pl: "Smok",
              },
            ],
            gallery_file_ids: [
              "f1111111-1111-1111-1111-111111111111",
              "f2222222-2222-2222-2222-222222222222",
              "f3333333-3333-3333-3333-333333333333",
            ],
            image_count: 3,
          },
          {
            id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            slug: "vase",
            name_en: "Vase",
            name_pl: "Wazon",
            category_id: "11111111-1111-1111-1111-111111111112",
            source: "unknown",
            status: "not_printed",
            rating: null,
            thumbnail_file_id: null,
            date_added: "2026-04-29",
            deleted_at: null,
            created_at: "2026-04-29T00:00:00Z",
            updated_at: "2026-04-29T00:00:00Z",
            tags: [],
            gallery_file_ids: [],
            image_count: 0,
          },
        ],
      }),
    }),
  );

  // Stub the file content endpoint so carousel images on the catalog list
  // resolve to a tiny valid PNG instead of failing/animating.
  await page.route("**/api/models/**/files/**/content**", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "base64",
      ),
    }),
  );
}

export async function stubSotDetail(page: Page) {
  const id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
  await page.route(`**/api/models/${id}`, (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id,
        slug: "dragon",
        name_en: "Dragon",
        name_pl: "Smok",
        category_id: "c1",
        source: "printables",
        status: "printed",
        rating: 4.5,
        thumbnail_file_id: null,
        date_added: "2026-04-12",
        deleted_at: null,
        created_at: "2026-04-12T00:00:00Z",
        updated_at: "2026-04-12T00:00:00Z",
        tags: [
          {
            id: "t1",
            slug: "dragon",
            name_en: "Dragon",
            name_pl: "Smok",
            group_id: "tg-theme",
            group_position: 0,
          },
          {
            id: "t2",
            slug: "articulated",
            name_en: "Articulated",
            name_pl: null,
            group_id: null,
            group_position: 0,
          },
        ],
        category: {
          id: "c1",
          parent_id: null,
          slug: "decorations",
          name_en: "Decorations",
          name_pl: "Dekoracje",
        },
        files: [
          {
            id: "f1",
            model_id: id,
            kind: "stl",
            original_name: "dragon.stl",
            storage_path: "",
            sha256: "",
            size_bytes: 1234567,
            mime_type: "model/stl",
            position: null,
            created_at: "",
          },
          {
            id: "f2",
            model_id: id,
            kind: "image",
            original_name: "iso.png",
            storage_path: "",
            sha256: "",
            size_bytes: 1024,
            mime_type: "image/png",
            position: null,
            created_at: "",
          },
        ],
        prints: [
          {
            id: "p1",
            model_id: id,
            photo_file_id: "f2",
            printed_at: "2026-04-30",
            note: "Printed in PETG 0.2mm",
            created_at: "",
            updated_at: "",
          },
        ],
        notes: [
          {
            id: "n1",
            model_id: id,
            kind: "description",
            body: "Articulated dragon for Bambu A1.",
            author_id: null,
            created_at: "",
            updated_at: "",
          },
          {
            id: "n2",
            model_id: id,
            kind: "operational",
            body: "0.2mm layer, supports off",
            author_id: null,
            created_at: "",
            updated_at: "",
          },
        ],
        external_links: [
          {
            id: "el1",
            model_id: id,
            source: "printables",
            external_id: "12345",
            url: "https://printables.com/m/12345",
            created_at: "",
            updated_at: "",
          },
        ],
      }),
    }),
  );
  // image content stub
  await page.route("**/api/models/**/files/**/content**", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "base64",
      ),
    }),
  );
  // Story 45.2 — TagGroupsSection's `/api/tag-groups` fixture. "Theme" carries
  // this model's tag `t1` (renders label + chip); "Material" carries none of
  // this model's tags (renders admin dash + Add, hidden for non-admins);
  // `t2` (above) is groupless, exercising the trailing "Ungrouped" section.
  // Together the three cover all three per-section rendering states in one
  // fixture.
  await page.route("**/api/tag-groups*", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        groups: [
          {
            id: "tg-theme",
            slug: "theme",
            name_en: "Theme",
            name_pl: "Motyw",
            position: 0,
            tags: [
              { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: "Smok", model_count: 1 },
            ],
          },
          {
            id: "tg-material",
            slug: "material",
            name_en: "Material",
            name_pl: "Materiał",
            position: 1,
            // Empty catalog-wide roster is fine here — TagGroupsSection only
            // consumes `detail.tags` filtered by `group_id`, never `group.tags`
            // (see Design Notes in spec-45-2), so this group's own tag list is
            // irrelevant to what it's exercising: zero of *this model's* tags.
            tags: [],
          },
        ],
        groupless: [
          { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null, model_count: 1 },
        ],
      }),
    }),
  );
}

/**
 * PROFILE-LIB-1 (AC-19) — stub the operator profile-library list/import/delete endpoints.
 *
 * The shared `_test.ts` fixture already authenticates as admin + 404s unstubbed `/api/*`;
 * this registers the library GET (curated blocks) so the inventory renders deterministically,
 * plus a POST handler whose status is controlled by `postRejection` (for the rejection state)
 * and a DELETE → 204. Curated metadata only — no raw Orca JSON.
 */
export async function stubProfileLibrary(
  page: Page,
  opts: {
    blocks?: unknown[];
    postRejection?: { status: number; reason_category: string };
  } = {},
) {
  const blocks = opts.blocks ?? [];
  await page.route("**/api/admin/profiles/library**", (route: Route) => {
    const method = route.request().method();
    if (method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ blocks }),
      });
    }
    if (method === "POST") {
      if (opts.postRejection) {
        return route.fulfill({
          status: opts.postRejection.status,
          contentType: "application/json",
          body: JSON.stringify({
            detail: {
              reason_category: opts.postRejection.reason_category,
              message: "rejected",
            },
          }),
        });
      }
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(blocks[0] ?? {}),
      });
    }
    if (method === "DELETE") {
      return route.fulfill({
        status: 204,
        contentType: "application/json",
        body: "",
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: "{}",
    });
  });
}

/**
 * PROFILE-OFFER-1 (AC-20) — stub the admin profile-offer + library-picker endpoints.
 *
 * Registers the offers list GET (curated offer DTOs, no raw Orca JSON), a POST whose status is
 * controlled by `postRejection` (the create-rejection state), PATCH → 200, DELETE → 204, plus
 * the library list GET so the compose pickers populate deterministically. The four projects
 * (desktop-light/dark, mobile-light/dark) are pixel-stable — no real validate/disk runs.
 */
export async function stubProfileOffers(
  page: Page,
  opts: {
    offers?: unknown[];
    library?: unknown[];
    postRejection?: { status: number; reason_category: string };
    /** Curated `POST /api/admin/profiles/offers/recompute-estimates` summary. */
    recompute?: unknown;
  } = {},
) {
  const offers = opts.offers ?? [];
  const library = opts.library ?? [];
  await page.route("**/api/admin/profiles/library**", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ blocks: library }),
    }),
  );
  await page.route("**/api/admin/profiles/offers**", (route: Route) => {
    const method = route.request().method();
    if (method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ offers }),
      });
    }
    if (method === "POST") {
      if (opts.postRejection) {
        return route.fulfill({
          status: opts.postRejection.status,
          contentType: "application/json",
          body: JSON.stringify({
            detail: {
              reason_category: opts.postRejection.reason_category,
              message: "rejected",
            },
          }),
        });
      }
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(offers[0] ?? {}),
      });
    }
    if (method === "PATCH") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(offers[0] ?? {}),
      });
    }
    if (method === "DELETE") {
      return route.fulfill({
        status: 204,
        contentType: "application/json",
        body: "",
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: "{}",
    });
  });
  // Registered after the generic offers route because Playwright resolves matching routes in
  // reverse registration order; the recompute subpath must not be treated as offer create.
  await page.route(
    "**/api/admin/profiles/offers/recompute-estimates**",
    (route: Route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(
          opts.recompute ?? {
            dry_run: true,
            inspected: 0,
            cells_total: 0,
            cells_resolved: 0,
            cells_resolve_failed: 0,
            would_enqueue: 0,
            enqueued: 0,
            already_fresh: 0,
            missing_stl: 0,
            errors: 0,
          },
        ),
      }),
  );
}

/**
 * ADMIN-JOBS-1 (AC-22) — stub `GET /api/admin/queues` for the read-only queue console.
 *
 * Serves a curated snapshot DTO (allowlist fields only — no raw args/kwargs/result), or a
 * 500 for the fails-closed state. The four projects (desktop-light/dark, mobile-light/dark)
 * are pixel-stable: the payload is identical on every poll and carries no rendered timestamp.
 */
export async function stubAdminQueues(
  page: Page,
  opts: { snapshot?: unknown; error?: boolean } = {},
) {
  await page.route("**/api/admin/queues**", (route: Route) => {
    if (opts.error) {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(opts.snapshot ?? {}),
    });
  });
}
