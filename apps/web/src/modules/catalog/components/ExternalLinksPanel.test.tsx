import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ExternalLinksPanel } from "./ExternalLinksPanel";
import type { ExternalLinkRead } from "@/lib/api-types";

afterEach(() => cleanup());

const LINK: ExternalLinkRead = {
  id: "l1",
  model_id: "m1",
  source: "printables",
  external_id: "12345",
  url: "https://printables.com/m/12345",
  created_at: "",
  updated_at: "",
};

describe("ExternalLinksPanel", () => {
  it("renders nothing when there are no links", () => {
    const { container } = render(<ExternalLinksPanel links={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders each link as an anchor with target=_blank", () => {
    render(<ExternalLinksPanel links={[LINK]} />);
    const anchor = screen.getByRole("link");
    expect(anchor.getAttribute("href")).toBe(LINK.url);
    expect(anchor.getAttribute("target")).toBe("_blank");
    expect(anchor.getAttribute("rel")).toContain("noopener");
  });

  it("renders the source pill", () => {
    render(<ExternalLinksPanel links={[LINK]} />);
    expect(screen.getByText("printables")).toBeTruthy();
  });
});
