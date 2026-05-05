import type { Page, Route } from "@playwright/test";

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

export async function stubSotDetail(page: Page) {
  const id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
  await page.route(`**/api/models/${id}`, (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id,
        legacy_id: "001",
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
          { id: "t1", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
          { id: "t2", slug: "articulated", name_en: "Articulated", name_pl: null },
        ],
        category: { id: "c1", parent_id: null, slug: "decorations", name_en: "Decorations", name_pl: "Dekoracje" },
        files: [
          { id: "f1", model_id: id, kind: "stl", original_name: "dragon.stl", storage_path: "", sha256: "", size_bytes: 1234567, mime_type: "model/stl", position: null, created_at: "" },
          { id: "f2", model_id: id, kind: "image", original_name: "iso.png", storage_path: "", sha256: "", size_bytes: 1024, mime_type: "image/png", position: null, created_at: "" },
        ],
        prints: [
          { id: "p1", model_id: id, photo_file_id: "f2", printed_at: "2026-04-30", note: "Printed in PETG 0.2mm", created_at: "", updated_at: "" },
        ],
        notes: [
          { id: "n1", model_id: id, kind: "description", body: "Articulated dragon for Bambu A1.", author_id: null, created_at: "", updated_at: "" },
          { id: "n2", model_id: id, kind: "operational", body: "0.2mm layer, supports off", author_id: null, created_at: "", updated_at: "" },
        ],
        external_links: [
          { id: "el1", model_id: id, source: "printables", external_id: "12345", url: "https://printables.com/m/12345", created_at: "", updated_at: "" },
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
}
