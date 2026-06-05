import { test, expect } from "@playwright/test";

test("search → configure → build → done (mocked API + injected EventSource)", async ({ page }) => {
  // Inject a controllable fake EventSource BEFORE the app loads (R10 — page.route SSE is unreliable).
  await page.addInitScript(() => {
    class FakeES {
      onmessage: ((e: any) => void) | null = null;
      onerror: ((e: any) => void) | null = null;
      private L: Record<string, Function[]> = {};
      constructor(public url: string) {
        (window as any).__es = this;
      }
      addEventListener(t: string, cb: Function) {
        (this.L[t] ||= []).push(cb);
      }
      close() {}
      _emit(d: string) {
        this.onmessage?.({ data: d });
      }
      _end() {
        (this.L["end"] || []).forEach((c) => c({}));
      }
    }
    (window as any).EventSource = FakeES as any;
  });

  await page.route("**/resolve", (r) =>
    r.fulfill({
      json: {
        candidates: [
          {
            scrip_code: "532790",
            company: "Tanla Platforms Ltd",
            is_primary: true,
            isin: "INE483C01032",
            symbol: "TANLA",
          },
        ],
      },
    }),
  );
  await page.route("**/build", (r) => r.fulfill({ status: 202, json: { job_id: "j1" } }));
  await page.route("**/build/j1", (r) =>
    r.fulfill({
      json: {
        job_id: "j1",
        status: "done",
        progress: null,
        result: { downloaded: 1, skipped: 0, failed: 0 },
        error: null,
      },
    }),
  );
  await page.route("**/library**", (r) => r.fulfill({ json: { companies: [] } }));
  await page.route("**/open-folder", (r) => r.fulfill({ json: { ok: true } }));

  await page.goto("/");
  await page.getByPlaceholder(/name or BSE code/i).fill("tan");
  // Pick from the dropdown row specifically (the name also re-appears in the config header).
  await page.getByRole("option").filter({ hasText: "Tanla Platforms Ltd" }).click();
  await page.getByRole("button", { name: /Get the filings/i }).click();

  // Wait until the app has constructed the (fake) EventSource, then drive it:
  // one progress frame, then the terminal frame + the named "end" event.
  await page.waitForFunction(() => Boolean((window as any).__es));
  await page.evaluate(() => {
    const es: any = (window as any).__es;
    es._emit(
      JSON.stringify({ stage: "download", current: 1, total: 1, message: "Annual Report", percent: 100 }),
    );
    es._emit(JSON.stringify({ status: "done", result: { downloaded: 1, skipped: 0, failed: 0 }, error: null }));
    es._end();
  });

  await expect(page.getByText(/Your TANLA library is ready/)).toBeVisible({ timeout: 5000 });
});
