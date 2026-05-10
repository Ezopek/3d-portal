import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CardCarousel } from "./CardCarousel";

afterEach(() => cleanup());

const MODEL_ID = "11111111-1111-1111-1111-111111111111";
const IDS = [
  "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
  "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
  "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
];

function urlFor(fileId: string) {
  return `/api/models/${MODEL_ID}/files/${fileId}/content`;
}

const dotsQuery = { name: /^go to image / };

describe("CardCarousel", () => {
  it("renders the first image as the main one", () => {
    render(<CardCarousel modelId={MODEL_ID} fileIds={IDS} alt="Dragon" />);
    const img = document.querySelector("img") as HTMLImageElement;
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe(urlFor(IDS[0]!));
    expect(img.getAttribute("alt")).toBe("Dragon");
  });

  it("renders N dot buttons when fileIds.length >= 2", () => {
    render(<CardCarousel modelId={MODEL_ID} fileIds={IDS} alt="Dragon" />);
    const dots = screen.getAllByRole("button", dotsQuery);
    expect(dots).toHaveLength(IDS.length);
    dots.forEach((dot, i) => {
      expect(dot.getAttribute("aria-label")).toBe(`go to image ${i + 1}`);
    });
  });

  it("renders no dots when fileIds.length === 1", () => {
    render(
      <CardCarousel modelId={MODEL_ID} fileIds={[IDS[0]!]} alt="Dragon" />,
    );
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.queryByTestId("card-carousel-dots")).toBeNull();
  });

  it("clicking a dot switches the main image", async () => {
    render(<CardCarousel modelId={MODEL_ID} fileIds={IDS} alt="Dragon" />);
    const img = () => document.querySelector("img") as HTMLImageElement;
    expect(img().getAttribute("src")).toBe(urlFor(IDS[0]!));

    const dots = screen.getAllByRole("button", dotsQuery);
    fireEvent.click(dots[2]!);
    await waitFor(() => {
      expect(img().getAttribute("src")).toBe(urlFor(IDS[2]!));
    });

    fireEvent.click(dots[1]!);
    await waitFor(() => {
      expect(img().getAttribute("src")).toBe(urlFor(IDS[1]!));
    });
  });

  it("clicking a dot does not propagate to wrapping link / preventDefault is called", () => {
    const wrapperClick = vi.fn();
    render(
      <a
        href="/catalog/some-id"
        onClick={(e) => {
          wrapperClick({
            defaultPrevented: e.defaultPrevented,
            propagationStopped: false,
          });
        }}
      >
        <CardCarousel modelId={MODEL_ID} fileIds={IDS} alt="Dragon" />
      </a>,
    );

    const dots = screen.getAllByRole("button", dotsQuery);
    fireEvent.click(dots[1]!);

    expect(wrapperClick).not.toHaveBeenCalled();
  });
});
