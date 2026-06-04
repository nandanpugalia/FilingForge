import { it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import * as api from "../api";

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
  vi.spyOn(api, "getLibrary").mockResolvedValue([]); });
afterEach(() => vi.restoreAllMocks());

it("walks search → configure → building → done", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue([
    { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, isin: "INE483C01032", symbol: "TANLA" }]);
  vi.spyOn(api, "startBuild").mockResolvedValue("j1");
  vi.spyOn(api, "openFolder").mockResolvedValue(undefined);
  vi.spyOn(api, "subscribeBuildEvents").mockImplementation((_id, h) => {
    h.onProgress({ stage: "download", current: 1, total: 1, message: "Annual Report", percent: 100 });
    h.onEnd({ status: "done", result: { downloaded: 1, skipped: 0, failed: 0 } });
    return { close: () => {} };
  });
  render(<App />);
  await userEvent.type(screen.getByPlaceholderText(/name or BSE code/i), "tan");
  await userEvent.click(await screen.findByText(/Tanla Platforms Ltd/));
  await userEvent.click(await screen.findByRole("button", { name: /Get the filings/i }));
  expect(await screen.findByText(/Your TANLA library is ready/)).toBeInTheDocument();
  expect(screen.getByText(/1 documents added/)).toBeInTheDocument();
});

it("shows a friendly error if startBuild fails, and Retry re-runs", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue([
    { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, symbol: "TANLA" }]);
  const sb = vi.spyOn(api, "startBuild").mockRejectedValueOnce(new Error("BSE isn't responding right now."));
  render(<App />);
  await userEvent.type(screen.getByPlaceholderText(/name or BSE code/i), "tan");
  await userEvent.click(await screen.findByText(/Tanla Platforms Ltd/));
  await userEvent.click(await screen.findByRole("button", { name: /Get the filings/i }));
  expect(await screen.findByText(/BSE isn't responding/)).toBeInTheDocument();
  // Retry: make the second attempt succeed enough to leave the error screen
  sb.mockResolvedValueOnce("j2");
  vi.spyOn(api, "subscribeBuildEvents").mockImplementation((_id, h) => {
    h.onEnd({ status: "done", result: { downloaded: 0, skipped: 0, failed: 0 } }); return { close: () => {} }; });
  await userEvent.click(screen.getByRole("button", { name: /Retry/i }));
  expect(await screen.findByText(/library is ready/i)).toBeInTheDocument();
});
