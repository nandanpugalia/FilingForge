import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as api from "../api";

beforeEach(() => { vi.restoreAllMocks(); });
afterEach(() => { vi.unstubAllGlobals(); });

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body } as Response);
}

describe("resolve", () => {
  it("returns candidates incl isin + symbol", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { candidates: [
      { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, isin: "INE483C01032", symbol: "TANLA" }] }));
    const out = await api.resolve("tanla");
    expect(out[0].scrip_code).toBe("532790");
    expect(out[0].isin).toBe("INE483C01032");
    expect(out[0].symbol).toBe("TANLA");
  });
  it("throws friendly message on error status", async () => {
    vi.stubGlobal("fetch", mockFetch(503, { user_message: "BSE isn't responding right now." }));
    await expect(api.resolve("x")).rejects.toThrow("BSE isn't responding right now.");
  });
  it("throws a friendly message when the backend is not running (fetch rejects)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.resolve("x")).rejects.toThrow(/couldn't reach the engine/i);
  });
});

describe("startBuild / getStatus / getLibrary / openFolder", () => {
  it("startBuild posts scope and returns job_id", async () => {
    const f = mockFetch(202, { job_id: "j1" }); vi.stubGlobal("fetch", f);
    const id = await api.startBuild({ scrip_code: "532790", ticker: "TANLA", dest: "/x", years: 1, everything: true, categories: [] });
    expect(id).toBe("j1");
    expect(JSON.parse((f.mock.calls[0][1] as RequestInit).body as string).everything).toBe(true);
  });
  it("getStatus returns the snapshot", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { job_id: "j1", status: "done", result: { downloaded: 9, skipped: 1, failed: 0 }, progress: null, error: null }));
    expect((await api.getStatus("j1")).result?.downloaded).toBe(9);
  });
  it("getLibrary returns companies", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { companies: [{ ticker: "TANLA", total: 42, counts: { "annual-reports": 1 } }] }));
    expect((await api.getLibrary("/root"))[0].ticker).toBe("TANLA");
  });
  it("openFolder posts the path", async () => {
    const f = mockFetch(200, { ok: true }); vi.stubGlobal("fetch", f);
    await api.openFolder("/root/TANLA");
    expect(f).toHaveBeenCalledWith(expect.stringContaining("/open-folder"), expect.anything());
  });
  it("importPendingPdf posts the exact slot and returns remaining pending items", async () => {
    const f = mockFetch(200, { news_id: "news-1", destination: "/lib/KFINTECH/report.pdf", pending: [] });
    vi.stubGlobal("fetch", f);

    const out = await api.importPendingPdf("/lib", "KFINTECH", "news-1", "/Users/np/Downloads/report.pdf");

    expect(out.destination).toBe("/lib/KFINTECH/report.pdf");
    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/pending/import");
    expect(JSON.parse(init.body as string)).toEqual({
      root: "/lib", ticker: "KFINTECH", news_id: "news-1", path: "/Users/np/Downloads/report.pdf",
    });
  });
});

describe("payments worker: startCheckout / redeem / redeemFallback / installSkillMd", () => {
  it("startCheckout makes a UUID session, POSTs /checkout, returns {url, session}", async () => {
    const f = mockFetch(200, { url: "https://rzp.io/i/abc" }); vi.stubGlobal("fetch", f);
    const out = await api.startCheckout();
    expect(out.url).toBe("https://rzp.io/i/abc");
    expect(out.session).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    const [calledUrl, init] = f.mock.calls[0] as [string, RequestInit];
    expect(calledUrl).toContain("/checkout");
    expect(JSON.parse(init.body as string).session).toBe(out.session);
  });
  it("startCheckout throws friendly when the worker fails", async () => {
    vi.stubGlobal("fetch", mockFetch(502, {}));
    await expect(api.startCheckout()).rejects.toThrow(/checkout/i);
  });
  it("redeem 200 returns the md text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => "# SKILL MD" } as Response));
    const r = await api.redeem("s1");
    expect(r).toEqual({ status: "ready", md: "# SKILL MD" });
  });
  it("redeem 202 is pending; 403/404 are notfound; offline is pending", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 202, text: async () => "" } as Response));
    expect((await api.redeem("s")).status).toBe("pending");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403, text: async () => "" } as Response));
    expect((await api.redeem("s")).status).toBe("notfound");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, text: async () => "" } as Response));
    expect((await api.redeem("s")).status).toBe("notfound");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    expect((await api.redeem("s")).status).toBe("pending");
  });
  it("redeemFallback POSTs session + payment_id and returns md on 200", async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => "MD" } as Response);
    vi.stubGlobal("fetch", f);
    const r = await api.redeemFallback("s1", "pay_123");
    expect(r).toEqual({ status: "ready", md: "MD" });
    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body).toEqual({ session: "s1", payment_id: "pay_123" });
  });
  it("installSkillMd POSTs name+content to the engine /skills/install", async () => {
    const f = mockFetch(200, { skill: { id: "concall-decoder", name: "Concall Decoder", tier: "Premium", desc: "", prompt: "x", imported: true } });
    vi.stubGlobal("fetch", f);
    const s = await api.installSkillMd("Concall Decoder", "# MD");
    expect(s.id).toBe("concall-decoder");
    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/skills/install");
    expect(JSON.parse(init.body as string)).toEqual({ name: "Concall Decoder", content: "# MD" });
  });
});

describe("apiBase uses the runtime engine port", () => {
  beforeEach(() => { vi.resetModules(); });
  afterEach(() => {
    vi.doUnmock("../components/ReadyGate");
    vi.doUnmock("@tauri-apps/api/core");
    vi.unstubAllGlobals();
    vi.resetModules();
  });
  it("routes calls to the port engine_info reports (8766), not hardcoded 8765", async () => {
    vi.doMock("../components/ReadyGate", () => ({ isTauri: () => true }));
    vi.doMock("@tauri-apps/api/core", () => ({ invoke: vi.fn().mockResolvedValue({ port: 8766, token: "tok" }) }));
    const freshApi = await import("../api");
    const f = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ companies: [] }) } as Response);
    vi.stubGlobal("fetch", f);
    await freshApi.getLibrary("/root");
    expect(f.mock.calls[0][0] as string).toContain("127.0.0.1:8766");
    const url = await freshApi.reportUrl("ACME/research_report/business_model.html");
    expect(url).toBe("http://127.0.0.1:8766/lib/ACME/research_report/business_model.html?token=tok");
  });
});
