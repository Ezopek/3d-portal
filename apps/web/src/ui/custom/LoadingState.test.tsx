import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import "@/locales/i18n";

import { LoadingState } from "./LoadingState";

afterEach(() => {
  cleanup();
});

describe("LoadingState", () => {
  it("spinner variant exposes role=status with localized label", () => {
    render(<LoadingState variant="spinner" />);
    const node = screen.getByRole("status");
    expect(node.getAttribute("aria-label")).toMatch(/Loading|Ładowanie/);
  });

  it("skeleton-grid renders cols*rows placeholders", () => {
    const { container } = render(
      <LoadingState variant="skeleton-grid" cols={3} rows={2} />,
    );
    expect(container.querySelectorAll(".animate-pulse").length).toBe(6);
  });

  it("skeleton-detail renders multiple animated placeholders for hero + columns", () => {
    const { container } = render(<LoadingState variant="skeleton-detail" />);
    // Hero (2) + image (1) + 3 right-side blocks + tab strip (1) = 7
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThanOrEqual(6);
  });

  it("accepts a custom label prop overriding the default", () => {
    render(<LoadingState variant="spinner" label="Loading models" />);
    expect(screen.getByRole("status").getAttribute("aria-label")).toBe(
      "Loading models",
    );
  });
});
