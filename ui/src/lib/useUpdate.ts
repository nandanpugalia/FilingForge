import { useEffect, useState, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
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

// Auto-update state machine. The check/install are driven by the app's Rust commands
// (`check_for_update` / `install_update`), which hold the update internally and honor the
// `beta` channel toggle. The user's library lives outside the app bundle, so an update can
// never touch their filings. All of this short-circuits on non-Tauri builds via isTauri().
export type UpdateState =
  | { phase: "idle" }
  | { phase: "checking" }
  | { phase: "uptodate" }
  | { phase: "available"; version: string; notes?: string }
  | { phase: "downloading"; pct: number }
  | { phase: "ready" }
  | { phase: "error"; message: string };

export type UpdateController = {
  state: UpdateState;
  install: () => Promise<void>;
  dismiss: () => void;
  checkNow: () => void;
};

export function useUpdate(beta: boolean): UpdateController {
  const [state, setState] = useState<UpdateState>({ phase: "idle" });

  // force=true is a user-initiated "Check for updates" (Settings) — bypasses the throttle and
  // surfaces "checking"/"uptodate"/"error". force=false is the silent, throttled auto-check.
  const runCheck = useCallback(async (force: boolean) => {
    if (!isTauri()) return;
    const last = Number(localStorage.getItem(LAST_CHECK_KEY) || 0) || null;
    if (!force && !shouldAutoCheck(last, Date.now())) return;   // throttled — skip silently
    if (force) setState({ phase: "checking" });
    try {
      const info = await invoke<{ version: string; notes: string | null } | null>("check_for_update", { beta });
      localStorage.setItem(LAST_CHECK_KEY, String(Date.now()));
      if (info) setState({ phase: "available", version: info.version, notes: info.notes ?? undefined });
      else if (force) setState({ phase: "uptodate" });
    } catch (e) {
      // an unreachable feed is non-fatal — the app works fine offline. Only surface it on a
      // manual check; the silent auto-check just stays idle.
      if (force) setState({ phase: "error", message: String(e) });
    }
  }, [beta]);

  useEffect(() => { void runCheck(false); }, [runCheck]);   // auto, throttled, on launch

  const install = useCallback(async () => {
    if (!isTauri()) return;
    setState({ phase: "downloading", pct: 0 });
    const un1 = await listen<number>("update://progress", (e) => setState({ phase: "downloading", pct: e.payload }));
    const un2 = await listen("update://done", () => setState({ phase: "ready" }));
    try { await invoke("install_update", { beta }); }
    catch (e) { setState({ phase: "error", message: String(e) }); }
    finally { un1(); un2(); }
  }, [beta]);

  const dismiss = () => setState({ phase: "idle" });
  const checkNow = useCallback(() => { void runCheck(true); }, [runCheck]);

  return { state, install, dismiss, checkNow };
}
