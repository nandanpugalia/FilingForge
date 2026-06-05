import { useUpdate } from "../lib/useUpdate";

// A slim banner at the top of the window when a signed update is available.
// "Install & restart" downloads + verifies + installs, then relaunches.
export function UpdateBanner() {
  const { state, install, dismiss } = useUpdate();
  if (state.phase === "idle") return null;
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
