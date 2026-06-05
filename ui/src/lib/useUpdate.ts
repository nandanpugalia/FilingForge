import { useEffect, useState, useCallback } from "react";
import { isTauri } from "../components/ReadyGate";

// How often the app auto-checks for updates. We throttle to once/24h (rather than every
// launch) so the updater's latest.json fetch — which GitHub counts as our privacy-clean
// "active install" signal — stays ~1/day/install instead of being inflated by relaunches.
export const UPDATE_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;
const LAST_CHECK_KEY = "ff_last_update_check";

/** Pure throttle decision: auto-check only if we've never checked, or it's been >=24h. */
export function shouldAutoCheck(lastCheckMs: number | null, nowMs: number): boolean {
  if (!lastCheckMs) return true;
  return nowMs - lastCheckMs >= UPDATE_CHECK_INTERVAL_MS;
}

// Auto-update state machine. Dynamic-imports the Tauri updater/process plugins so the
// browser/preview/test builds (non-Tauri) never load them. Feed + signature are configured
// in tauri.conf.json > plugins.updater; the user's library lives outside the app bundle, so
// an update can never touch their filings.
export type UpdateState =
  | { phase: "idle" }
  | { phase: "checking" }
  | { phase: "uptodate" }
  | { phase: "available"; version: string; notes?: string }
  | { phase: "downloading"; pct: number }
  | { phase: "ready" }
  | { phase: "error"; message: string };

// the updater's Update object — typed loosely to avoid importing the plugin at module load
type TauriUpdate = {
  version: string; body?: string;
  downloadAndInstall: (cb: (e: { event: string; data?: { contentLength?: number; chunkLength?: number } }) => void) => Promise<void>;
};

export type UpdateController = {
  state: UpdateState;
  install: () => Promise<void>;
  dismiss: () => void;
  checkNow: () => void;
};

export function useUpdate(): UpdateController {
  const [state, setState] = useState<UpdateState>({ phase: "idle" });
  const [update, setUpdate] = useState<TauriUpdate | null>(null);

  // force=true is a user-initiated "Check for updates" (Settings) — bypasses the throttle and
  // surfaces "checking"/"uptodate"/"error". force=false is the silent, throttled auto-check.
  const runCheck = useCallback(async (force: boolean) => {
    if (!isTauri()) return;
    const last = Number(localStorage.getItem(LAST_CHECK_KEY) || 0) || null;
    if (!force && !shouldAutoCheck(last, Date.now())) return;   // throttled — skip silently
    if (force) setState({ phase: "checking" });
    try {
      const { check } = await import("@tauri-apps/plugin-updater");
      const u = (await check()) as TauriUpdate | null;
      localStorage.setItem(LAST_CHECK_KEY, String(Date.now()));
      if (u) { setUpdate(u); setState({ phase: "available", version: u.version, notes: u.body }); }
      else if (force) setState({ phase: "uptodate" });
    } catch (e) {
      // an unreachable feed is non-fatal — the app works fine offline. Only surface it on a
      // manual check; the silent auto-check just stays idle.
      if (force) setState({ phase: "error", message: (e as Error).message });
    }
  }, []);

  useEffect(() => { void runCheck(false); }, [runCheck]);   // auto, throttled, on launch

  const install = async () => {
    if (!update) return;
    try {
      let total = 0, got = 0;
      await update.downloadAndInstall((e) => {
        if (e.event === "Started") total = e.data?.contentLength ?? 0;
        else if (e.event === "Progress") {
          got += e.data?.chunkLength ?? 0;
          setState({ phase: "downloading", pct: total ? Math.round((got / total) * 100) : 0 });
        } else if (e.event === "Finished") setState({ phase: "ready" });
      });
      const { relaunch } = await import("@tauri-apps/plugin-process");
      await relaunch();
    } catch (e) {
      setState({ phase: "error", message: (e as Error).message });
    }
  };

  const dismiss = () => setState({ phase: "idle" });
  const checkNow = useCallback(() => { void runCheck(true); }, [runCheck]);

  return { state, install, dismiss, checkNow };
}
