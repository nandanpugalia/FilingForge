import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as api from "../api";

class FakeES {
  static last: FakeES; url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null; closed = false;
  listeners: Record<string, ((e: MessageEvent) => void)[]> = {};
  constructor(url: string) { this.url = url; FakeES.last = this; }
  addEventListener(t: string, cb: (e: MessageEvent) => void) { (this.listeners[t] ||= []).push(cb); }
  emit(data: string) { this.onmessage?.({ data } as MessageEvent); }
  fireEnd() { (this.listeners["end"] || []).forEach(cb => cb({} as MessageEvent)); }
  fireError() { this.onerror?.({} as Event); }
  close() { this.closed = true; }
}
beforeEach(() => { vi.stubGlobal("EventSource", FakeES as unknown as typeof EventSource); });
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

// The EventSource is now created after apiBase() resolves (a microtask), so
// flush pending microtasks before reaching for FakeES.last.
const flush = () => new Promise<void>((r) => setTimeout(r, 0));

describe("subscribeBuildEvents", () => {
  it("delivers progress, resolves on event:end with the terminal frame, closes once", async () => {
    const events: any[] = []; let ended: any = undefined;
    api.subscribeBuildEvents("j1", { onProgress: e => events.push(e), onEnd: t => { ended = t; } });
    await flush();
    FakeES.last.emit(JSON.stringify({ stage: "download", current: 1, total: 2, message: "a", percent: 50 }));
    FakeES.last.emit(JSON.stringify({ status: "done", result: { downloaded: 2, skipped: 0, failed: 0 }, error: null }));
    FakeES.last.fireEnd();
    expect(events[0].current).toBe(1);
    expect(ended.status).toBe("done");
    expect(FakeES.last.closed).toBe(true);
  });

  it("does NOT double-resolve when onerror fires after end", async () => {
    let calls = 0;
    api.subscribeBuildEvents("j1", { onProgress: () => {}, onEnd: () => { calls++; } });
    await flush();
    FakeES.last.fireEnd();      // resolves once
    FakeES.last.fireError();    // must be ignored (already settled)
    expect(calls).toBe(1);
  });

  it("on transient onerror (status still running) does NOT resolve; resolves when status becomes done", async () => {
    const statuses = [
      { job_id: "j1", status: "running", progress: null, result: null, error: null },
      { job_id: "j1", status: "done", progress: null, result: { downloaded: 1, skipped: 0, failed: 0 }, error: null },
    ];
    vi.spyOn(api, "getStatus").mockImplementation(async () => statuses.shift() as any);
    let ended: any = undefined;
    api.subscribeBuildEvents("j1", { onProgress: () => {}, onEnd: t => { ended = t; } });
    await flush();
    await FakeES.last.fireError();      // status=running → no resolve
    await new Promise(r => setTimeout(r, 0));
    expect(ended).toBeUndefined();
    await FakeES.last.fireError();      // status=done → resolve
    await new Promise(r => setTimeout(r, 0));
    expect(ended?.status).toBe("done");
  });
});
