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
        notes: "",
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

  await page.route("**/api/catalog/models/001/files", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        files: [
          "Dragon.stl",
          "images/Dragon.png",
          "images/Dragon-detail.png",
        ],
      }),
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
