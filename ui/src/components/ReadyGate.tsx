import { useEffect, useState, type ReactNode } from "react";
import { apiBase } from "../api";

/** True only inside the Tauri webview (the desktop app). */
export function isTauri(): boolean {
  return typeof window !== "undefined" &&
    typeof (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== "undefined";
}

const POLL_MS = 500;
const TIMEOUT_MS = 45_000; // sidecar cold start is ~12s; give generous headroom

// Rotating boot status lines — modern-smart-software feel while the engine warms up.
const BOOT_LINES = [
  "Starting the engine…",
  "Warming up the index…",
  "Reaching BSE…",
  "Almost there…",
];
const ROTATE_MS = 2_000;
const SLOW_MS = 15_000; // after this, reassure that first launch is slower
const SLOW_LINE = "Hang tight — first launch is a little slower…";

async function pingHealth(signal: AbortSignal): Promise<boolean> {
  try {
    // Poll the SAME port the Rust shell chose for the sidecar (engine_info is available
    // immediately at webview load), not a hardcoded 8765 — otherwise a non-default port
    // would hang the splash forever. apiBase() resolves to 8765 in non-Tauri builds.
    const base = await apiBase();
    const res = await fetch(`${base}/health`, { signal });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Gates the app behind the engine sidecar's readiness.
 *
 * In the desktop app (Tauri) the Python engine is spawned at launch and takes
 * several seconds to start serving on the shell-chosen loopback port, so we poll
 * /health and show a themed splash until it's up. In a plain web build (or tests) there is
 * no sidecar to wait for, so children render immediately.
 */
export function ReadyGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState<boolean>(() => !isTauri());
  const [lineIdx, setLineIdx] = useState(0);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (ready) return;
    const ctrl = new AbortController();
    let stopped = false;
    const deadline = Date.now() + TIMEOUT_MS;

    const tick = async () => {
      if (stopped) return;
      if (await pingHealth(ctrl.signal)) {
        if (!stopped) setReady(true);
        return;
      }
      if (Date.now() < deadline && !stopped) setTimeout(tick, POLL_MS);
    };
    tick();

    return () => { stopped = true; ctrl.abort(); };
  }, [ready]);

  // Rotate the status line every ~2s; flip to the "slower" reassurance after a while.
  useEffect(() => {
    if (ready) return;
    const rotate = setInterval(() => setLineIdx((i) => (i + 1) % BOOT_LINES.length), ROTATE_MS);
    const slowTimer = setTimeout(() => setSlow(true), SLOW_MS);
    return () => { clearInterval(rotate); clearTimeout(slowTimer); };
  }, [ready]);

  if (ready) return <>{children}</>;

  const line = slow ? SLOW_LINE : BOOT_LINES[lineIdx];
  return (
    <div className="splash" role="status" aria-live="polite">
      <div className="splash-mark">FilingForge</div>
      <div className="splash-ember" aria-hidden="true" />
      <div key={line} className="splash-msg splash-msg-rotate">{line}</div>
    </div>
  );
}
