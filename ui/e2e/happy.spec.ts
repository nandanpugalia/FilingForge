import { test, expect } from "@playwright/test";

declare global {
  interface Window {
    __happyEs?: { emit(data: string): void; end(): void };
  }
}

test("search → configure → preview → build → done", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("filingforge.settings", JSON.stringify({
      dest: "/Users/test/FilingForgeLibrary", years: 1, everything: true,
      categories: ["annual_report", "results", "investor_ppt", "concall"],
      openWhenDone: false, beta: false,
    }));

    class FakeEventSource {
      onmessage: ((event: MessageEvent<string>) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      private listeners: Record<string, Array<() => void>> = {};
      constructor(public url: string) {
        window.__happyEs = {
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
    scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true,
    isin: "INE483C01032", symbol: "TANLA",
  }] } }));
  await page.route("**/preview", (route) => route.fulfill({ json: {
    total: 1, new: 1, have: 0, by_category: [{ label: "Annual Reports", count: 1 }],
  } }));
  await page.route("**/build", (route) => route.fulfill({ status: 202, json: { job_id: "j1" } }));
  await page.route("**/build/j1", (route) => route.fulfill({ json: {
    job_id: "j1", status: "done", progress: null,
    result: { downloaded: 1, skipped: 0, failed: 0, pending: [] }, error: null,
  } }));
  await page.route("**/library**", (route) => route.fulfill({ json: { companies: [] } }));
  await page.route("**/open-folder", (route) => route.fulfill({ json: { ok: true } }));

  await page.goto("/");
  await page.getByPlaceholder(/look up a company/i).fill("tan");
  await page.getByRole("option").filter({ hasText: "Tanla Platforms Ltd" }).click();
  await page.getByRole("button", { name: /Build library/i }).click();
  await page.getByRole("button", { name: /Download 1/i }).click();

  await page.waitForFunction(() => Boolean(window.__happyEs));
  await page.evaluate(() => {
    window.__happyEs?.emit(JSON.stringify({
      stage: "download", current: 1, total: 1, message: "Annual Report", percent: 100,
    }));
    window.__happyEs?.emit(JSON.stringify({
      status: "done", result: { downloaded: 1, skipped: 0, failed: 0, pending: [] }, error: null,
    }));
    window.__happyEs?.end();
  });

  await expect(page.getByRole("heading", { name: "Library ready" })).toBeVisible({ timeout: 5000 });
  await expect(page.getByText("Tanla Platforms Ltd")).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy AI instructions" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open library" })).toBeVisible();
});
