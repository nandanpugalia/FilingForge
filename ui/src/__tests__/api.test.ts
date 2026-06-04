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
    await expect(api.resolve("x")).rejects.toThrow(/isn't running/i);
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
});
