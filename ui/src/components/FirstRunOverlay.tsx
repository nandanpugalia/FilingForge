import { useState } from "react";
import { pickFolder } from "../lib/pickFolder";
import { isTauri } from "../lib/isTauri";

// One-time setup, shown on first launch only. Asks a single thing — where the
// library is stored — and saves it as the global destination. Every build and the
// library view then use this one location, so they can never diverge. Changeable
// later in Settings.
export function FirstRunOverlay({ defaultDest, onComplete }: {
  defaultDest: string; onComplete: (dest: string) => void;
}) {
  const [dest, setDest] = useState(defaultDest);

  const browse = async () => {
    const p = await pickFolder(dest);
    if (p) setDest(p);
  };

  return (
    <div className="firstrun" role="dialog" aria-label="Set up your library">
      <div className="firstrun-card">
        <span className="wordmark">FilingForge<span className="wm-dot">.</span></span>
        <h2>Set up your library</h2>
        <p className="firstrun-sub">
          FilingForge keeps every company's filings in one folder on your computer.
          Choose where it lives — you can change this anytime in Settings.
        </p>
        <label className="firstrun-field">Library folder
          <span className="dest-row">
            <input aria-label="Library folder" value={dest} onChange={(e) => setDest(e.target.value)} />
            {isTauri() && (
              <button type="button" className="browse" onClick={browse}>Browse…</button>
            )}
          </span>
        </label>
        <button className="primary" onClick={() => onComplete(dest.trim() || defaultDest)}>Continue</button>
      </div>
    </div>
  );
}
