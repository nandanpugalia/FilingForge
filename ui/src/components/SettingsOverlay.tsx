import { useState } from "react";
import type { Settings } from "../types";
import { DONATE } from "../config";
export function SettingsOverlay({ settings, onSave, onClose }: {
  settings: Settings; onSave: (s: Settings) => void; onClose: () => void;
}) {
  const [s, setS] = useState(settings);
  return (
    <div className="overlay" role="dialog" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <button className="close" aria-label="close" onClick={onClose}>✕</button>
        <h3>Settings</h3>
        <label>Default library folder
          <input value={s.dest} onChange={(e) => setS({ ...s, dest: e.target.value })} /></label>
        <label>Default years
          <input type="number" min={1} max={25} value={s.years}
            onChange={(e) => setS({ ...s, years: Number(e.target.value) })} /></label>
        <label><input type="checkbox" checked={s.openWhenDone}
          onChange={(e) => setS({ ...s, openWhenDone: e.target.checked })} /> Open folder when done</label>
        <button className="primary" onClick={() => { onSave(s); onClose(); }}>Save</button>
        <section className="support">
          <h4>Support FilingForge</h4>
          <p className="warm">FilingForge is free. If it saves you time, you can chip in — entirely optional.</p>
          <img className="qr" src="/upi.png" alt="UPI QR — scan to support" width={140} height={140} />
          <div className="qr-note">{DONATE.upiNote}</div>
          <a className="btn" href={DONATE.sponsors} target="_blank" rel="noreferrer">GitHub Sponsors ↗</a>
          <a className="btn" href={DONATE.bmc} target="_blank" rel="noreferrer">Buy Me a Coffee ↗</a>
        </section>
      </div>
    </div>
  );
}
