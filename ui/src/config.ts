// NOTE: the engine base URL is NOT a constant — it's resolved at runtime from the port the
// Rust shell chose, via apiBase()/engineInfo() in api.ts. Don't reintroduce a hardcoded base
// here: a non-8765 port would silently bypass it and break the app.
export const SEARCH_DEBOUNCE_MS = 250;
// Injected at build/test time from src-tauri/tauri.conf.json (see vite.config.ts) so it
// ALWAYS matches the real native version. Never hardcode this — it silently drifted to
// "0.1.10" once and made every build report the wrong version (and broke OTA detection).
declare const __APP_VERSION__: string;
export const APP_VERSION = typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "0.0.0";
export const ISSUES_URL = "https://github.com/nandanpugalia/FilingForge/issues/new";
// Worker endpoint that receives bug/feature reports. Empty until deployed —
// when empty the report form degrades gracefully (no network, friendly thanks).
export const BUG_WORKER_URL = import.meta.env.VITE_BUG_WORKER_URL ?? "";
// Payments Worker (Razorpay checkout + redeem) for premium skills. Deployed Cloudflare
// Worker; override at build time with VITE_WORKER_URL if it ever moves. Tests mock fetch.
export const WORKER_URL =
  import.meta.env.VITE_WORKER_URL ?? "https://filingforge-pay.bhaavbhagwanhai.workers.dev";
// UPI-only support. Real FilingForge-noted QR (/upi.png) + VPA.
export const DONATE = {
  upiId: "nandanpugalia@okicici",
  upiNote: "Scan with any UPI app to support",
};
