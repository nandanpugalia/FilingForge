import type { UpdateState } from "../lib/useUpdate";

// A slim banner at the top of the window when a signed update is available.
// "Install & restart" downloads + verifies + installs, then relaunches. The update
// state is owned by App (so the banner and the Settings "Check for updates" button
// share one source of truth); this component is purely presentational.
export function UpdateBanner({ state, install, dismiss }: {
  state: UpdateState;
  install: () => Promise<void>;
  dismiss: () => void;
}) {
  // idle / checking / uptodate have nothing to show in the banner (checking + uptodate
  // are surfaced in Settings instead).
  if (!state || state.phase === "idle" || state.phase === "checking" || state.phase === "uptodate") return null;
  return (
    <div className="update-banner" role="status">
      {state.phase === "available" && (
        <>
          <span className="ub-msg"><span className="ub-dot" />FilingForge {state.version} is available.</span>
          <span className="ub-actions">
            <button className="ub-install" onClick={install}>Install &amp; restart</button>
            <button className="ub-later" onClick={dismiss}>Later</button>
          </span>
        </>
      )}
      {state.phase === "downloading" && <span className="ub-msg">Downloading update… {state.pct}%</span>}
      {state.phase === "ready" && <span className="ub-msg">Update ready — restarting…</span>}
      {state.phase === "error" && (
        <>
          <span className="ub-msg">Couldn't update: {state.message}</span>
          <button className="ub-later" onClick={dismiss}>Dismiss</button>
        </>
      )}
    </div>
  );
}
