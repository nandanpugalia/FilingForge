// NOTE: the engine base URL is NOT a constant — it's resolved at runtime from the port the
// Rust shell chose, via apiBase()/engineInfo() in api.ts. Don't reintroduce a hardcoded base
// here: a non-8765 port would silently bypass it and break the app.
export const SEARCH_DEBOUNCE_MS = 250;
export const APP_VERSION = "0.1.9";
export const ISSUES_URL = "https://github.com/nandanpugalia/FilingForge/issues/new";
// Worker endpoint that receives bug/feature reports. Empty until deployed —
// when empty the report form degrades gracefully (no network, friendly thanks).
export const BUG_WORKER_URL = import.meta.env.VITE_BUG_WORKER_URL ?? "";
// Payments Worker (Razorpay checkout + redeem) for premium skills. Placeholder —
// the real URL is filled at deploy via VITE_WORKER_URL. Tests mock fetch, so the
// value here doesn't matter to them.
export const WORKER_URL =
  import.meta.env.VITE_WORKER_URL ?? "https://filingforge-worker.example.workers.dev";
// UPI-only support. Real FilingForge-noted QR (/upi.png) + VPA.
export const DONATE = {
  upiId: "nandanpugalia@okicici",
  upiNote: "Scan with any UPI app to support",
};
