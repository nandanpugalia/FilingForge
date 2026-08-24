import { it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import * as api from "../api";
import * as picker from "../lib/pickPdfFile";
import * as external from "../lib/openExternal";

// jsdom 29 omits Web Storage; provide a minimal localStorage so loadSettings/saveSettings work.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  const ls: Storage = {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (k) => (store.has(k) ? store.get(k)! : null),
    key: (i) => Array.from(store.keys())[i] ?? null,
    removeItem: (k) => { store.delete(k); },
    setItem: (k, v) => { store.set(k, String(v)); },
  };
  Object.defineProperty(globalThis, "localStorage", { value: ls, configurable: true });
  Object.defineProperty(window, "localStorage", { value: ls, configurable: true });
}

beforeEach(() => { vi.restoreAllMocks(); localStorage.clear();
  // Seed saved settings so these flow tests skip the one-time first-run setup.
  localStorage.setItem("filingforge.settings", JSON.stringify({
    dest: "~/FilingForgeLibrary", years: 1, everything: true,
    categories: ["annual_report","results","investor_ppt","concall"], openWhenDone: true }));
  vi.spyOn(api, "getLibrary").mockResolvedValue([]); });
afterEach(() => vi.restoreAllMocks());

it("walks search → configure → preview → building → done", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue([
    { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, isin: "INE483C01032", symbol: "TANLA" }]);
  vi.spyOn(api, "previewBuild").mockResolvedValue({ total: 1, new: 1, have: 0, by_category: [{ label: "Annual Reports", count: 1 }] });
  vi.spyOn(api, "startBuild").mockResolvedValue("j1");
  vi.spyOn(api, "openFolder").mockResolvedValue(undefined);
  vi.spyOn(api, "subscribeBuildEvents").mockImplementation((_id, h) => {
    h.onProgress({ stage: "download", current: 1, total: 1, message: "Annual Report", percent: 100 });
    h.onEnd({ status: "done", result: { downloaded: 1, skipped: 0, failed: 0 } });
    return { close: () => {} };
  });
  const { container } = render(<App />);
  // search phase: the titlebar wordmark is hidden (only the big centre wordmark shows)
  expect(container.querySelector(".titlebar .wordmark")).toBeNull();
  await userEvent.type(screen.getByPlaceholderText(/look up a company/i), "tan");
  await userEvent.click(await screen.findByText(/Tanla Platforms Ltd/));
  // after picking a company (configure phase) the titlebar wordmark appears
  expect(container.querySelector(".titlebar .wordmark")).not.toBeNull();
  await userEvent.click(await screen.findByRole("button", { name: /Build library/i }));
  // preview gate → approve
  await userEvent.click(await screen.findByRole("button", { name: /Download 1/i }));
  expect(await screen.findByText(/Your Tanla Platforms Ltd library is ready/)).toBeInTheDocument();
  expect(screen.getByText(/1 document added/)).toBeInTheDocument();
});

it("shows a friendly error if startBuild fails, and Retry re-runs", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue([
    { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, symbol: "TANLA" }]);
  vi.spyOn(api, "previewBuild").mockResolvedValue({ total: 1, new: 1, have: 0, by_category: [] });
  const sb = vi.spyOn(api, "startBuild").mockRejectedValueOnce(new Error("BSE isn't responding right now."));
  render(<App />);
  await userEvent.type(screen.getByPlaceholderText(/look up a company/i), "tan");
  await userEvent.click(await screen.findByText(/Tanla Platforms Ltd/));
  await userEvent.click(await screen.findByRole("button", { name: /Build library/i }));
  await userEvent.click(await screen.findByRole("button", { name: /Download 1/i }));
  expect(await screen.findByText(/BSE isn't responding/)).toBeInTheDocument();
  // Retry: make the second attempt succeed enough to leave the error screen
  sb.mockResolvedValueOnce("j2");
  vi.spyOn(api, "subscribeBuildEvents").mockImplementation((_id, h) => {
    h.onEnd({ status: "done", result: { downloaded: 0, skipped: 0, failed: 0 } }); return { close: () => {} }; });
  await userEvent.click(screen.getByRole("button", { name: /Retry/i }));
  expect(await screen.findByText(/library is ready/i)).toBeInTheDocument();
});

it("completes one pending source PDF through the native picker and local API", async () => {
  const pending = {
    news_id: "news-1", date: "2026-07-28", headline: "Annual Report FY 2025-26",
    folder: "annual-reports", category: "Annual Reports", expected_type: "Annual report",
    expected_period: "FY 2025-26", bse_url: "https://www.bseindia.com/notice.pdf",
    issuer_url: "https://investor.kfintech.com/annual-reports/", reason: "ambiguous issuer page",
  };
  vi.spyOn(api, "resolve").mockResolvedValue([
    { scrip_code: "543210", company: "KFin Technologies", is_primary: true, symbol: "KFINTECH" }]);
  vi.spyOn(api, "previewBuild").mockResolvedValue({ total: 2, new: 2, have: 0, by_category: [] });
  vi.spyOn(api, "startBuild").mockResolvedValue("j1");
  vi.spyOn(api, "openFolder").mockResolvedValue(undefined);
  vi.spyOn(api, "subscribeBuildEvents").mockImplementation((_id, h) => {
    h.onEnd({ status: "done", result: { downloaded: 1, skipped: 0, failed: 0, pending: [pending] } });
    return { close: () => {} };
  });
  const openSource = vi.spyOn(external, "openExternal").mockResolvedValue(undefined);
  vi.spyOn(picker, "pickPdfFile").mockResolvedValue("/Users/np/Downloads/report.pdf");
  const importPdf = vi.spyOn(api, "importPendingPdf").mockResolvedValue({
    news_id: "news-1", destination: "/lib/KFINTECH/report.pdf", pending: [],
  });

  render(<App />);
  await userEvent.type(screen.getByPlaceholderText(/look up a company/i), "kfin");
  await userEvent.click(await screen.findByText("KFin Technologies"));
  await userEvent.click(await screen.findByRole("button", { name: /Build library/i }));
  await userEvent.click(await screen.findByRole("button", { name: /Download 2/i }));

  await userEvent.click(await screen.findByRole("button", { name: /Get document/i }));
  expect(openSource).toHaveBeenCalledWith(pending.issuer_url);
  await userEvent.click(screen.getByRole("button", { name: /Use downloaded PDF/i }));

  expect(importPdf).toHaveBeenCalledWith("~/FilingForgeLibrary", "KFINTECH", "news-1", "/Users/np/Downloads/report.pdf");
  expect(await screen.findByText(/Your KFin Technologies library is ready/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Use downloaded PDF/i })).not.toBeInTheDocument();
});

it("resumes a persisted pending PDF from the library after an app restart", async () => {
  const pending = {
    news_id: "news-1", date: "2026-07-28", headline: "Annual Report FY 2025-26",
    folder: "annual-reports", category: "Annual Reports", expected_type: "Annual report",
    expected_period: "FY 2025-26", bse_url: "https://www.bseindia.com/notice.pdf",
    issuer_url: "https://investor.kfintech.com/annual-reports/", reason: "source PDF needed",
  };
  vi.mocked(api.getLibrary).mockResolvedValue([
    { ticker: "KFINTECH", total: 12, counts: { "annual-reports": 12 }, pending: 1, hasReport: false, reportRel: null },
  ]);
  vi.spyOn(api, "getPending").mockResolvedValue([pending]);
  vi.spyOn(picker, "pickPdfFile").mockResolvedValue("/Users/np/Downloads/report.pdf");
  const importPdf = vi.spyOn(api, "importPendingPdf").mockResolvedValue({
    news_id: "news-1", destination: "/lib/KFINTECH/report.pdf", pending: [],
  });

  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: "Library" }));
  await userEvent.click(await screen.findByRole("button", { name: /Complete remaining/i }));

  expect(await screen.findByText(/12 documents ready · 1 awaiting source PDF/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Use downloaded PDF/i }));

  expect(importPdf).toHaveBeenCalledWith(
    "~/FilingForgeLibrary", "KFINTECH", "news-1", "/Users/np/Downloads/report.pdf",
  );
  expect(await screen.findByText(/Your KFINTECH library is ready/i)).toBeInTheDocument();
});
