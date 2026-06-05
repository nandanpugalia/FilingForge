import { useEffect, useState } from "react";
import { isTauri } from "../components/ReadyGate";

// Auto-update state machine. Dynamic-imports the Tauri updater/process plugins so
// the browser/preview/test builds (non-Tauri) never load them. Feed + signature
// are configured in tauri.conf.json > plugins.updater; the user's library lives
// outside the app bundle, so an update can never touch their filings.
export type UpdateState =
  | { phase: "idle" }
  | { phase: "available"; version: string; notes?: string }
  | { phase: "downloading"; pct: number }
  | { phase: "ready" }
  | { phase: "error"; message: string };

// the updater's Update object — typed loosely to avoid importing the plugin at module load
type TauriUpdate = {
  version: string; body?: string;
  downloadAndInstall: (cb: (e: { event: string; data?: { contentLength?: number; chunkLength?: number } }) => void) => Promise<void>;
};

export function useUpdate() {
  const [state, setState] = useState<UpdateState>({ phase: "idle" });
  const [update, setUpdate] = useState<TauriUpdate | null>(null);

  useEffect(() => {
    if (!isTauri()) return;
    let cancelled = false;
    (async () => {
      try {
        const { check } = await import("@tauri-apps/plugin-updater");
        const u = (await check()) as TauriUpdate | null;
        if (!cancelled && u) { setUpdate(u); setState({ phase: "available", version: u.version, notes: u.body }); }
      } catch {
        // a missing/unreachable feed is non-fatal — the app works fine offline
        if (!cancelled) setState({ phase: "idle" });
      }
    })();
    return () => { cancelled = true; };
  }, []);

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
  return { state, install, dismiss };
}
