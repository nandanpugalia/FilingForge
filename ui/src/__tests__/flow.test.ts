import { describe, it, expect } from "vitest";
import { reducer, initialState } from "../flow";
import type { State } from "../flow";
import type { Candidate } from "../types";

const cand: Candidate = { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, isin: "INE483C01032", symbol: "TANLA" };
const prog = (n: number) => ({ stage: "download", current: n, total: 12, message: `item ${n}`, percent: n * 8 });

describe("flow reducer", () => {
  it("starts in search with empty log", () => {
    expect(initialState.phase).toBe("search");
    expect(initialState.progressLog).toEqual([]);
  });
  it("PICK_COMPANY → configure with the company", () => {
    const s = reducer(initialState, { type: "PICK_COMPANY", candidate: cand });
    expect(s.phase).toBe("configure"); expect(s.company?.scrip_code).toBe("532790");
  });
  it("CHANGE_COMPANY → back to a clean search", () => {
    const s = reducer(reducer(initialState, { type: "PICK_COMPANY", candidate: cand }), { type: "CHANGE_COMPANY" });
    expect(s.phase).toBe("search"); expect(s.company).toBeNull();
  });
  it("START_BUILD → building, resets progress + log", () => {
    const s = reducer({ ...initialState, phase: "configure", progressLog: ["old"] }, { type: "START_BUILD", jobId: "j1" });
    expect(s.phase).toBe("building"); expect(s.jobId).toBe("j1"); expect(s.progressLog).toEqual([]);
  });
  it("PROGRESS updates progress + appends to log (only while building)", () => {
    let s = reducer({ ...initialState, phase: "building" }, { type: "PROGRESS", progress: prog(1) });
    s = reducer(s, { type: "PROGRESS", progress: prog(2) });
    expect(s.progress?.current).toBe(2);
    expect(s.progressLog).toEqual(["item 1", "item 2"]);
  });
  it("PROGRESS is ignored when NOT building (phase guard)", () => {
    const s = reducer({ ...initialState, phase: "search" }, { type: "PROGRESS", progress: prog(1) });
    expect(s).toEqual({ ...initialState, phase: "search" });   // unchanged
  });
  it("progressLog caps at 200 entries", () => {
    let s: State = { ...initialState, phase: "building" };
    for (let i = 0; i < 250; i++) s = reducer(s, { type: "PROGRESS", progress: prog(i) });
    expect(s.progressLog.length).toBe(200);
    expect(s.progressLog[s.progressLog.length - 1]).toBe("item 249");
  });
  it("BUILD_DONE → done (only from building; ignored otherwise)", () => {
    const ok = reducer({ ...initialState, phase: "building" }, { type: "BUILD_DONE", result: { downloaded: 9, skipped: 1, failed: 0, pending: [] } });
    expect(ok.phase).toBe("done"); expect(ok.result?.downloaded).toBe(9);
    const ignored = reducer({ ...initialState, phase: "search" }, { type: "BUILD_DONE", result: { downloaded: 9, skipped: 1, failed: 0, pending: [] } });
    expect(ignored.phase).toBe("search");
  });
  it("PENDING_IMPORTED increments ready count and replaces remaining slots", () => {
    const done: State = {
      ...initialState,
      phase: "done",
      result: { downloaded: 1, skipped: 0, failed: 0, pending: [{
        news_id: "news-1", date: "2026-07-28", headline: "Annual Report",
        folder: "annual-reports", category: "Annual Reports", expected_type: "Annual report",
        expected_period: "FY 2025-26", bse_url: "https://www.bseindia.com/notice.pdf",
        issuer_url: null, reason: "missing link",
      }] },
    };

    const next = reducer(done, { type: "PENDING_IMPORTED", pending: [] });

    expect(next.result?.downloaded).toBe(2);
    expect(next.result?.pending).toEqual([]);
  });
  it("RESUME_PENDING restores a persisted completion flow after reopening", () => {
    const pending = [{
      news_id: "news-1", date: "2026-07-28", headline: "Annual Report",
      folder: "annual-reports", category: "Annual Reports", expected_type: "Annual report",
      expected_period: "FY 2025-26", bse_url: "https://www.bseindia.com/notice.pdf",
      issuer_url: null, reason: "source PDF needed",
    }];

    const next = reducer(initialState, {
      type: "RESUME_PENDING", candidate: { ...cand, company: "KFINTECH", symbol: "KFINTECH" },
      result: { downloaded: 12, skipped: 0, failed: 0, pending },
    });

    expect(next.phase).toBe("done");
    expect(next.company?.symbol).toBe("KFINTECH");
    expect(next.result?.pending).toEqual(pending);
  });
  it("FAIL → error with message", () => {
    const s = reducer(initialState, { type: "FAIL", message: "BSE isn't responding." });
    expect(s.phase).toBe("error"); expect(s.error).toBe("BSE isn't responding.");
  });
  it("BACK_TO_CONFIGURE → configure, keeps company, clears job/progress (from building)", () => {
    const built = reducer(reducer(initialState, { type: "PICK_COMPANY", candidate: cand }), { type: "START_BUILD", jobId: "j1" });
    const s = reducer({ ...built, progressLog: ["x"], progress: prog(3) }, { type: "BACK_TO_CONFIGURE" });
    expect(s.phase).toBe("configure");
    expect(s.company?.scrip_code).toBe("532790");   // company kept so they can tweak + rebuild
    expect(s.jobId).toBeNull(); expect(s.progress).toBeNull(); expect(s.progressLog).toEqual([]);
  });
  it("BACK_TO_CONFIGURE → configure from error (keeps company)", () => {
    const errored = reducer(reducer(initialState, { type: "PICK_COMPANY", candidate: cand }), { type: "FAIL", message: "boom" });
    const s = reducer(errored, { type: "BACK_TO_CONFIGURE" });
    expect(s.phase).toBe("configure"); expect(s.company?.scrip_code).toBe("532790"); expect(s.error).toBeNull();
  });
  it("BACK_TO_CONFIGURE is a no-op without a company / from other phases", () => {
    expect(reducer({ ...initialState, phase: "search" }, { type: "BACK_TO_CONFIGURE" }).phase).toBe("search");
    expect(reducer({ ...initialState, phase: "building", company: null }, { type: "BACK_TO_CONFIGURE" }).phase).toBe("building");
  });
  it("RESET → clean search", () => {
    const s = reducer({ ...initialState, phase: "done" }, { type: "RESET" });
    expect(s.phase).toBe("search"); expect(s.company).toBeNull();
  });
});
