import { describe, expect, it } from "vitest";

import { pickGalleryCandidates } from "./galleryCandidates";

const baseModel = {
  id: "001",
  path: "decorum/dragon",
  prints: [],
};

describe("pickGalleryCandidates", () => {
  it("returns empty when nothing matches", () => {
    const result = pickGalleryCandidates(baseModel, []);
    expect(result).toEqual([
      { url: "/api/files/001/iso.png", path: "iso.png" },
      { url: "/api/files/001/front.png", path: "front.png" },
      { url: "/api/files/001/side.png", path: "side.png" },
      { url: "/api/files/001/top.png", path: "top.png" },
    ]);
  });

  it("includes catalog images in listed order", () => {
    const result = pickGalleryCandidates(baseModel, [
      "Dragon.stl",
      "images/a.png",
      "images/b.jpg",
      "notes.txt",
    ]);
    expect(result.slice(0, 2)).toEqual([
      { url: "/api/files/001/images/a.png", path: "images/a.png" },
      { url: "/api/files/001/images/b.jpg", path: "images/b.jpg" },
    ]);
  });

  it("includes prints from model.prints sorted by date desc and stripped of model prefix", () => {
    const model = {
      id: "001",
      path: "decorum/dragon",
      prints: [
        {
          path: "decorum/dragon/prints/2026-04-15.jpg",
          date: "2026-04-15",
          notes_en: "",
          notes_pl: "",
        },
        {
          path: "decorum/dragon/prints/2026-04-30.jpg",
          date: "2026-04-30",
          notes_en: "",
          notes_pl: "",
        },
      ],
    };
    const result = pickGalleryCandidates(model, []);
    expect(result[0]).toEqual({
      url: "/api/files/001/prints/2026-04-30.jpg",
      path: "prints/2026-04-30.jpg",
    });
    expect(result[1]).toEqual({
      url: "/api/files/001/prints/2026-04-15.jpg",
      path: "prints/2026-04-15.jpg",
    });
  });

  it("falls back to prints/*.{jpg,png,webp} from files listing when model.prints is empty", () => {
    const result = pickGalleryCandidates(baseModel, [
      "Dragon.stl",
      "prints/2026-04-15-front.jpg",
      "prints/2026-04-30-back.png",
    ]);
    expect(result.slice(0, 2).map((c) => c.path)).toEqual([
      "prints/2026-04-15-front.jpg",
      "prints/2026-04-30-back.png",
    ]);
  });

  it("prefers model.prints over files listing for prints (avoids duplicates)", () => {
    const model = {
      id: "001",
      path: "decorum/dragon",
      prints: [
        {
          path: "decorum/dragon/prints/2026-04-30.jpg",
          date: "2026-04-30",
          notes_en: "",
          notes_pl: "",
        },
      ],
    };
    const result = pickGalleryCandidates(model, [
      "prints/2026-04-30.jpg",
      "prints/2026-05-01.jpg",
    ]);
    const printPaths = result.map((c) => c.path).filter((p) => p.startsWith("prints/"));
    expect(printPaths).toEqual(["prints/2026-04-30.jpg"]);
  });

  it("appends 4 renders after catalog images and prints", () => {
    const result = pickGalleryCandidates(baseModel, ["images/a.png"]);
    expect(result.map((c) => c.path)).toEqual([
      "images/a.png",
      "iso.png",
      "front.png",
      "side.png",
      "top.png",
    ]);
  });

  it("dedupes by path preserving order", () => {
    const result = pickGalleryCandidates(baseModel, ["iso.png", "images/a.png"]);
    expect(result.map((c) => c.path)).toEqual([
      "images/a.png",
      "iso.png",
      "front.png",
      "side.png",
      "top.png",
    ]);
  });

  it("ignores files outside images/ that are not images", () => {
    const result = pickGalleryCandidates(baseModel, [
      "Dragon.stl",
      "notes.txt",
      "metadata.json",
    ]);
    expect(result.map((p) => p.path)).toEqual([
      "iso.png",
      "front.png",
      "side.png",
      "top.png",
    ]);
  });

  it("matches png/jpg/jpeg/webp case-insensitively in images/", () => {
    const result = pickGalleryCandidates(baseModel, [
      "images/A.PNG",
      "images/b.JPG",
      "images/c.JPEG",
      "images/d.WEBP",
    ]);
    expect(result.slice(0, 4).map((c) => c.path)).toEqual([
      "images/A.PNG",
      "images/b.JPG",
      "images/c.JPEG",
      "images/d.WEBP",
    ]);
  });
});
