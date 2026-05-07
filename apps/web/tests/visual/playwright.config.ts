import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  snapshotPathTemplate: "{testDir}/__snapshots__/{testFilePath}/{arg}-{projectName}{ext}",
  fullyParallel: true,
  use: {
    baseURL: "http://localhost:5173",
    locale: "pl-PL",
    timezoneId: "Europe/Warsaw",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    {
      name: "desktop-light",
      use: { ...devices["Desktop Chrome"], colorScheme: "light" },
    },
    {
      name: "desktop-dark",
      use: { ...devices["Desktop Chrome"], colorScheme: "dark" },
    },
    {
      name: "mobile-light",
      use: { ...devices["Pixel 5"], colorScheme: "light" },
    },
    {
      name: "mobile-dark",
      use: { ...devices["Pixel 5"], colorScheme: "dark" },
    },
  ],
});
