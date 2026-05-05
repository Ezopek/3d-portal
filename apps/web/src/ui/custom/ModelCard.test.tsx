import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createMemoryHistory, createRootRoute, createRoute, createRouter, Outlet } from "@tanstack/react-router";
import { render, screen, cleanup } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { ModelCard } from "./ModelCard";
import type { ModelSummary } from "@/lib/api-types";
import "@/locales/i18n";

afterEach(() => cleanup());

function makeSummary(over: Partial<ModelSummary> = {}): ModelSummary {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    legacy_id: "001",
    slug: "dragon",
    name_en: "Dragon",
    name_pl: "Smok",
    category_id: "22222222-2222-2222-2222-222222222222",
    source: "printables",
    status: "printed",
    rating: 5,
    thumbnail_file_id: null,
    date_added: "2026-04-12",
    deleted_at: null,
    created_at: "2026-04-12T00:00:00Z",
    updated_at: "2026-04-12T00:00:00Z",
    tags: [
      { id: "33", slug: "dragon", name_en: "Dragon", name_pl: "Smok" },
      { id: "34", slug: "articulated", name_en: "Articulated", name_pl: null },
      { id: "35", slug: "extra-tag", name_en: "Extra", name_pl: null },
    ],
    ...over,
  };
}

async function renderWithRouter(node: ReactNode) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const card = createRoute({ getParentRoute: () => root, path: "/", component: () => <>{node}</> });
  const detail = createRoute({ getParentRoute: () => root, path: "/catalog/$id", component: () => null });
  const tree = root.addChildren([card, detail]);
  const router = createRouter({ routeTree: tree, history: createMemoryHistory({ initialEntries: ["/"] }) });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ModelCard (SoT)", () => {
  it("renders the localized title", async () => {
    await renderWithRouter(<ModelCard model={makeSummary()} />);
    // i18n test config defaults to 'en' — see locales/i18n.ts; fall back to name_en
    expect((await screen.findAllByText(/Dragon|Smok/)).length).toBeGreaterThan(0);
  });

  it("renders status and source badges", async () => {
    await renderWithRouter(<ModelCard model={makeSummary()} />);
    // StatusBadge / SourceBadge render 'printed' / 'printables' as text
    await screen.findAllByText(/Dragon|Smok/);
    expect(document.body.textContent?.toLowerCase()).toContain("printed");
    expect(document.body.textContent?.toLowerCase()).toContain("printables");
  });

  it("renders top 2 tag chips with slug labels", async () => {
    await renderWithRouter(<ModelCard model={makeSummary()} />);
    const chips = await screen.findAllByTestId("tag-chip");
    expect(chips).toHaveLength(2);
    const labels = chips.map((c) => c.textContent);
    expect(labels).toContain("dragon");
    expect(labels).toContain("articulated");
    expect(labels).not.toContain("extra-tag"); // overflow not rendered
  });

  it("emits a link to /catalog/<legacy_id> when legacy_id is set", async () => {
    await renderWithRouter(<ModelCard model={makeSummary()} />);
    await screen.findAllByText(/Dragon|Smok/);
    const link = document.querySelector("a") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe("/catalog/001");
  });

  it("falls back to /catalog/<uuid> when legacy_id is null", async () => {
    await renderWithRouter(<ModelCard model={makeSummary({ legacy_id: null })} />);
    await screen.findAllByText(/Dragon|Smok/);
    const link = document.querySelector("a") as HTMLAnchorElement;
    expect(link.getAttribute("href")).toBe("/catalog/11111111-1111-1111-1111-111111111111");
  });

  it("renders 'no preview' when thumbnail_file_id is null", async () => {
    await renderWithRouter(<ModelCard model={makeSummary({ thumbnail_file_id: null })} />);
    expect(await screen.findByText("no preview")).toBeTruthy();
  });

  it("renders an img with correct content URL when thumbnail_file_id is set", async () => {
    await renderWithRouter(
      <ModelCard model={makeSummary({ thumbnail_file_id: "44444444-4444-4444-4444-444444444444" })} />,
    );
    await screen.findAllByText(/Dragon|Smok/);
    const img = document.querySelector("img") as HTMLImageElement;
    expect(img.getAttribute("src")).toBe(
      "/api/models/11111111-1111-1111-1111-111111111111/files/44444444-4444-4444-4444-444444444444/content",
    );
  });
});
