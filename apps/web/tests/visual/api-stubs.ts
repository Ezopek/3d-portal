import type { Page, Route } from "@playwright/test";

export async function stubCatalog(page: Page) {
  await page.route("**/api/catalog/models", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        total: 2,
        models: [
          {
            id: "001",
            name_en: "Dragon",
            name_pl: "Smok",
            category: "decorations",
            tags: ["dragon", "smok"],
            source: "printables",
            status: "printed",
            rating: 5,
            thumbnail_url: null,
            has_3d: true,
            date_added: "2026-04-12",
            image_count: 3,
          },
          {
            id: "002",
            name_en: "Vase",
            name_pl: "Wazon",
            category: "decorations",
            tags: ["vase"],
            source: "unknown",
            status: "not_printed",
            rating: null,
            thumbnail_url: null,
            has_3d: true,
            date_added: "2026-04-29",
            image_count: 1,
          },
        ],
      }),
    }),
  );

  await page.route("**/api/catalog/models/001", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "001",
        name_en: "Dragon",
        name_pl: "Smok",
        path: "decorum/dragon",
        category: "decorations",
        subcategory: "",
        tags: ["dragon", "smok"],
        source: "printables",
        printables_id: "12345",
        thangs_id: null,
        makerworld_id: null,
        source_url: "https://printables.com/m/12345",
        rating: 5,
        status: "printed",
        notes: "Printed in PLA at 0.2mm layer height.\nSupports auto-generated.\nNo issues during 6-hour print.",
        thumbnail: null,
        thumbnail_url: "/api/files/001/images/Dragon.png",
        date_added: "2026-04-12",
        prints: [
          {
            path: "decorum/dragon/prints/2026-04-30-dragon.jpg",
            date: "2026-04-30",
            notes_en: "",
            notes_pl: "",
          },
        ],
      }),
    }),
  );

  // kind=printable → STL only; kind=all → all files (default for other consumers)
  await page.route("**/api/catalog/models/001/files*", (route: Route) => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get("kind");
    const files =
      kind === "printable"
        ? ["Dragon.stl"]
        : ["Dragon.stl", "images/Dragon.png", "images/Dragon-detail.png"];
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ files }),
    });
  });

  // Admin render-selection endpoint (required so networkidle resolves when logged in as admin).
  await page.route("**/api/admin/models/001/render-selection", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ paths: [], available_stls: ["Dragon.stl"] }),
    }),
  );

  await page.route("**/api/share/test-token", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "001",
        name_en: "Dragon",
        name_pl: "Smok",
        category: "decorations",
        tags: ["dragon"],
        thumbnail_url: null,
        has_3d: true,
        images: [],
        notes_en: "",
        notes_pl: "",
        stl_url: "/api/files/001/Dragon.stl?download=1",
      }),
    }),
  );

  // Catch-all image PNG response.
  await page.route("**/api/files/**", (route: Route) =>
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

/**
 * Like stubCatalog but the model has two STLs so the admin FileList shows
 * multiple checkboxes. The render-selection starts empty (auto/default state).
 */
export async function stubCatalogMultiStl(page: Page) {
  // Re-use all the catalog/list and model-detail routes from the base stub.
  await stubCatalog(page);

  // Override the files route with two STLs (kind=printable returns both).
  await page.route("**/api/catalog/models/001/files*", (route: Route) => {
    const url = new URL(route.request().url());
    const kind = url.searchParams.get("kind");
    const files =
      kind === "printable"
        ? ["Dragon-body.stl", "Dragon-wings.stl"]
        : ["Dragon-body.stl", "Dragon-wings.stl", "images/Dragon.png"];
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ files }),
    });
  });

  // Override render-selection with two available STLs, none selected (auto).
  await page.route("**/api/admin/models/001/render-selection", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        paths: [],
        available_stls: ["Dragon-body.stl", "Dragon-wings.stl"],
      }),
    }),
  );
}

export async function stubSotList(page: Page) {
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
              },
            ],
          },
          {
            id: "22222222-2222-2222-2222-222222222222",
            parent_id: null,
            slug: "tools",
            name_en: "Tools",
            name_pl: "Narzędzia",
            children: [],
          },
        ],
      }),
    }),
  );

  await page.route("**/api/tags*", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: "tag-1", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
        { id: "tag-2", slug: "articulated", name_en: "Articulated", name_pl: null },
      ]),
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
            legacy_id: "001",
            slug: "dragon",
            name_en: "Dragon",
            name_pl: "Smok",
            category_id: "11111111-1111-1111-1111-111111111111",
            source: "printables",
            status: "printed",
            rating: 5,
            thumbnail_file_id: null,
            date_added: "2026-04-12",
            deleted_at: null,
            created_at: "2026-04-12T00:00:00Z",
            updated_at: "2026-04-12T00:00:00Z",
            tags: [
              { id: "tag-1", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
            ],
          },
          {
            id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            legacy_id: "002",
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
          },
        ],
      }),
    }),
  );
}
