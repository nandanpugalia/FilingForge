// @vitest-environment jsdom
import { it, expect, beforeEach } from "vitest";
import { DEFAULT_SETTINGS, loadSettings, saveSettings } from "../settings";

// Node 26 exposes a native localStorage that requires --localstorage-file; polyfill with
// the same in-memory shim used by app.test.tsx so these unit tests work in all environments.
if (typeof globalThis.localStorage === "undefined" || globalThis.localStorage === null) {
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
}

beforeEach(() => localStorage.clear());

it("defaults pre-release (beta) to OFF", () => {
  expect(DEFAULT_SETTINGS.beta).toBe(false);
});

it("persists the beta preference", () => {
  saveSettings({ ...DEFAULT_SETTINGS, beta: true });
  expect(loadSettings().beta).toBe(true);
});
