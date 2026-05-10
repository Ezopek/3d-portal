import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

afterEach(() => {
  cleanup();
});

import "@/locales/i18n";

import { ComingSoonStub } from "./ComingSoonStub";

describe("ComingSoonStub", () => {
  it("renders the localized module name as a heading", () => {
    render(<ComingSoonStub moduleKey="queue" />);
    const headings = screen.getAllByRole("heading");
    expect(headings.length).toBeGreaterThan(0);
    expect(headings[0]?.textContent).toMatch(/Queue|Kolejka/);
  });

  it("renders the 'coming soon' subtitle", () => {
    render(<ComingSoonStub moduleKey="spools" />);
    expect(screen.getAllByText(/Coming soon|Wkrótce/).length).toBeGreaterThan(0);
  });

  it("renders an illustrative icon (svg) so the page does not look broken", () => {
    const { container } = render(<ComingSoonStub moduleKey="printer" />);
    // Lucide icons render as inline <svg>; a hero stub without any visual
    // signal looks like a partial render — guard against regression.
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
