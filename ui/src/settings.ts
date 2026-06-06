import type { Settings } from "./types";
const KEY = "filingforge.settings";
export const DEFAULT_SETTINGS: Settings = {
  // Default to the 4 high-signal types; "All filings" is an opt-in in Configure.
  // 2 years gives a trend (1 is too thin for analysis); the preview shows the count first.
  dest: "~/Documents/FilingForgeLibrary", years: 2, everything: false,
  categories: ["annual_report", "results", "investor_ppt", "concall"], openWhenDone: true,
};
export function loadSettings(): Settings {
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
  catch { return DEFAULT_SETTINGS; }
}
export function saveSettings(s: Settings): void { localStorage.setItem(KEY, JSON.stringify(s)); }

// First launch = the user has never saved settings (no key yet). Used to show the
// one-time setup that picks the library location before anything else.
export function isFirstRun(): boolean {
  try { return localStorage.getItem(KEY) === null; }
  catch { return false; }
}
