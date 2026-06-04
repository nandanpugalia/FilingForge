import type { Settings } from "./types";
const KEY = "filingforge.settings";
export const DEFAULT_SETTINGS: Settings = {
  dest: "~/FilingForgeLibrary", years: 1, everything: true,
  categories: ["annual_report", "results", "investor_ppt", "concall"], openWhenDone: true,
};
export function loadSettings(): Settings {
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
  catch { return DEFAULT_SETTINGS; }
}
export function saveSettings(s: Settings): void { localStorage.setItem(KEY, JSON.stringify(s)); }
