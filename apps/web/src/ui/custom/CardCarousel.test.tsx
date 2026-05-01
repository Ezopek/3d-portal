import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CardCarousel } from "./CardCarousel";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  // Vitest's `globals: false` config skips RTL's auto-cleanup hook, so DOM
  // from prior tests leaks into the next render. Clean up explicitly.
  cleanup();
  vi.unstubAllGlobals();
});

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const baseProps = {
  modelId: "001",
  modelPath: "decorum/dragon",
  prints: [],
  initialThumbnailUrl: "/api/files/001/images/a.png",
  imageCount: 3,
  alt: "Dragon",
};

describe("CardCarousel", () => {
  it("renders the initial thumbnail with srcSet", () => {
    render(<CardCarousel {...baseProps} />, { wrapper });
    const img = screen.getByRole("img", { name: "Dragon" }) as HTMLImageElement;
    expect(img.src).toContain("/api/files/001/images/a.png?w=480");
    expect(img.srcset).toContain("?w=480 1x");
    expect(img.srcset).toContain("?w=960 2x");
  });

  it("renders dot indicators when imageCount >= 2", () => {
    render(<CardCarousel {...baseProps} />, { wrapper });
    expect(screen.getAllByRole("button", { name: /go to image/i })).toHaveLength(3);
  });

  it("does not fire navigation when arrow is clicked (stopPropagation)", () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ files: ["images/a.png", "images/b.png"] }), {
        status: 200,
      }),
    );
    const onContainerClick = vi.fn();
    render(
      <a href="/anywhere" onClick={onContainerClick}>
        <CardCarousel {...baseProps} />
      </a>,
      { wrapper },
    );
    const next = screen.getByRole("button", { name: /next image/i });
    fireEvent.click(next);
    expect(onContainerClick).not.toHaveBeenCalled();
  });

  it("activates lazy fetch on first arrow click and lands on the second image", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          files: ["images/a.png", "images/b.png", "images/c.png"],
        }),
        { status: 200 },
      ),
    );
    render(<CardCarousel {...baseProps} />, { wrapper });
    const next = screen.getByRole("button", { name: /next image/i });
    // Pre-list click triggers activate(); index becomes 1 (clamped to imageCount-1).
    fireEvent.click(next);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => {
      const img = screen.getByRole("img", { name: "Dragon" }) as HTMLImageElement;
      // After list arrives, current image is list[1] = b.png.
      expect(img.src).toContain("/api/files/001/images/b.png");
    });
  });

  it("falls back to initial thumbnail when all gallery images error", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ files: ["images/missing-1.png", "images/missing-2.png"] }),
        { status: 200 },
      ),
    );
    render(<CardCarousel {...baseProps} />, { wrapper });
    const next = screen.getByRole("button", { name: /next image/i });
    fireEvent.click(next);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    // Simulate every gallery image failing — onError on each.
    const img = screen.getByRole("img", { name: "Dragon" }) as HTMLImageElement;
    fireEvent.error(img);
    fireEvent.error(img);

    await waitFor(() => {
      const finalImg = screen.getByRole("img", { name: "Dragon" }) as HTMLImageElement;
      expect(finalImg.src).toContain("/api/files/001/images/a.png");
    });
  });
});
