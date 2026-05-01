import { expect, test } from "@playwright/test";

import { stubCatalog } from "./api-stubs";
import { waitForReady } from "./helpers";

test("catalog list matches baseline", async ({ page }) => {
  await stubCatalog(page);
  await page.goto("/catalog");
  await waitForReady(page);
  await expect(page).toHaveScreenshot("catalog-list.png", { fullPage: true });
});

test("catalog list has no horizontal overflow", async ({ page, viewport }) => {
  await stubCatalog(page);
  await page.goto("/catalog");
  await waitForReady(page);
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(viewport!.width);
});

test("tag chips meet WCAG AA contrast", async ({ page }) => {
  await stubCatalog(page);
  await page.goto("/catalog");
  await waitForReady(page);
  const chip = page.locator('[data-testid="tag-chip"]').first();
  await chip.waitFor();
  const ratio = await chip.evaluate((el) => {
    const parseRgb = (str: string): [number, number, number] => {
      const match = str.match(/rgba?\(([^)]+)\)/);
      if (match === null) throw new Error(`Cannot parse color: ${str}`);
      const [r, g, b] = match[1].split(",").map((s) => Number(s.trim()));
      return [r, g, b];
    };
    const luminance = ([r, g, b]: [number, number, number]) => {
      const norm = (c: number) => {
        const s = c / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      };
      return 0.2126 * norm(r) + 0.7152 * norm(g) + 0.0722 * norm(b);
    };
    const cs = window.getComputedStyle(el);
    let bg = cs.backgroundColor;
    let walker: Element | null = el;
    while ((bg === "rgba(0, 0, 0, 0)" || bg === "transparent") && walker !== null) {
      walker = walker.parentElement;
      if (walker === null) break;
      bg = window.getComputedStyle(walker).backgroundColor;
    }
    const fgL = luminance(parseRgb(cs.color));
    const bgL = luminance(parseRgb(bg));
    const [hi, lo] = fgL > bgL ? [fgL, bgL] : [bgL, fgL];
    return (hi + 0.05) / (lo + 0.05);
  });
  expect(ratio).toBeGreaterThanOrEqual(4.5);
});
