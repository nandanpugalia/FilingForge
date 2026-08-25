import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

declare global {
  interface Window {
    __ffEs?: { emit(data: string): void; end(): void };
  }
}

const pending = {
  news_id: "news-1",
  date: "2026-07-28",
  headline: "Annual Report FY 2025-26",
  folder: "annual-reports",
  category: "Annual Reports",
  expected_type: "Annual report",
  expected_period: "FY 2025-26",
  bse_url: "https://www.bseindia.com/xml-data/corpfiling/AttachHis/notice.pdf",
  issuer_url: "https://investor.kfintech.com/annual-reports/",
  reason: "FilingForge could not select one unique replacement PDF safely.",
};

test("pending issuer document stays guided through PDF and Markdown completion", async ({ page }, testInfo) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.addInitScript(() => {
    localStorage.setItem("filingforge.settings", JSON.stringify({
      dest: "/Users/test/FilingForgeLibrary",
      years: 2,
      everything: false,
      categories: ["annual_report", "results", "investor_ppt", "concall"],
      openWhenDone: false,
      beta: false,
    }));

    class FakeEventSource {
      onmessage: ((event: MessageEvent<string>) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      private listeners: Record<string, Array<() => void>> = {};
      constructor(public url: string) {
        window.__ffEs = {
          emit: (data: string) => this.onmessage?.(new MessageEvent("message", { data })),
          end: () => (this.listeners.end || []).forEach((callback) => callback()),
        };
      }
      addEventListener(type: string, callback: () => void) {
        (this.listeners[type] ||= []).push(callback);
      }
      close() {}
    }

    Object.defineProperty(window, "EventSource", {
      configurable: true,
      value: FakeEventSource as unknown as typeof EventSource,
    });
  });

  await page.route("**/resolve", (route) => route.fulfill({ json: { candidates: [{
    scrip_code: "543210", company: "KFin Technologies", is_primary: true, symbol: "KFINTECH",
  }] } }));
  await page.route("**/preview", (route) => route.fulfill({ json: {
    total: 13, new: 13, have: 0, by_category: [{ label: "Annual Reports", count: 13 }],
  } }));
  await page.route("**/build", (route) => route.fulfill({ status: 202, json: { job_id: "pending-job" } }));
  await page.route("**/build/pending-job", (route) => route.fulfill({ json: {
    job_id: "pending-job", status: "done", progress: null,
    result: { downloaded: 12, skipped: 0, failed: 0, pending: [pending] }, error: null,
  } }));
  await page.route("**/library**", (route) => route.fulfill({ json: { companies: [] } }));
  await page.route("**/open-folder", (route) => route.fulfill({ json: { ok: true } }));
  await page.route("**/pending/import", async (route) => {
    const body = route.request().postDataJSON() as Record<string, string>;
    expect(body).toEqual({
      root: "/Users/test/FilingForgeLibrary",
      ticker: "KFINTECH",
      news_id: "news-1",
      path: "/Users/test/Downloads/KFin-Annual-Report.pdf",
    });
    await route.fulfill({ json: {
      news_id: "news-1",
      destination: "/Users/test/FilingForgeLibrary/KFINTECH/annual-reports/2026/report__news-1.pdf",
      pending: [],
    } });
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByPlaceholder(/look up a company/i).fill("kfin");
  await page.getByRole("option").filter({ hasText: "KFin Technologies" }).click();
  await page.getByRole("button", { name: /Build library/i }).click();
  await page.getByRole("button", { name: /Download 13/i }).click();

  await page.waitForFunction(() => Boolean(window.__ffEs));
  await page.evaluate((item) => {
    window.__ffEs?.emit(JSON.stringify({
      stage: "download", current: 13, total: 13,
      message: "Full document needs your download: Annual Report FY 2025-26", percent: 100,
    }));
    window.__ffEs?.emit(JSON.stringify({
      status: "done",
      result: { downloaded: 12, skipped: 0, failed: 0, pending: [item] },
      error: null,
    }));
    window.__ffEs?.end();
  }, pending);

  await expect(page.getByRole("heading", { name: "Library almost ready" })).toBeVisible();
  await expect(page.getByText("12 official filings ready")).toBeVisible();
  await expect(page.getByText("1 needs its source PDF")).toBeVisible();
  await expect(page.getByText("investor.kfintech.com")).toBeVisible();

  if (testInfo.project.name === "chromium") {
    const artifactDir = path.resolve(process.cwd(), "../output/playwright");
    mkdirSync(artifactDir, { recursive: true });
    await page.screenshot({ path: path.join(artifactDir, "pending-desktop-1440x900.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(artifactDir, "pending-mobile-390x844.png"), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 900 });
  }

  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("button", { name: "Get document" }).click();
  const popup = await popupPromise;
  expect(popup.url()).toContain("investor.kfintech.com");
  await popup.close();

  await page.evaluate(() => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {
        invoke: async (command: string) => {
          if (command === "plugin:path|resolve_directory") return "/Users/test/Downloads";
          if (command === "plugin:dialog|open") return "/Users/test/Downloads/KFin-Annual-Report.pdf";
          return null;
        },
      },
    });
  });

  await page.getByRole("button", { name: "Use downloaded PDF" }).click();
  await expect(page.getByRole("heading", { name: "Library ready" })).toBeVisible();
  await expect(page.getByText("KFin Technologies")).toBeVisible();
  await expect(page.getByRole("button", { name: "Use downloaded PDF" })).toHaveCount(0);
  expect(consoleErrors).toEqual([]);
});
