export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";
export const SEARCH_DEBOUNCE_MS = 250;
export const APP_VERSION = "0.1.7";
export const ISSUES_URL = "https://github.com/nandanpugalia/FilingForge/issues/new";
// Worker endpoint that receives bug/feature reports. Empty until deployed —
// when empty the report form degrades gracefully (no network, friendly thanks).
export const BUG_WORKER_URL = import.meta.env.VITE_BUG_WORKER_URL ?? "";
// UPI-only support. Real FilingForge-noted QR (/upi.png) + VPA.
export const DONATE = {
  upiId: "nandanpugalia@okicici",
  upiNote: "Scan with any UPI app to support",
};
