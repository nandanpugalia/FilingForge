import { useState } from "react";
import type { Settings } from "../types";
import { DONATE, APP_VERSION } from "../config";
import { pickFolder } from "../lib/pickFolder";
import { isTauri } from "./ReadyGate";
import { useEscapeClose } from "../lib/useEscapeClose";
import type { UpdateController } from "../lib/useUpdate";
export function SettingsOverlay({ settings, onSave, onClose, updater }: {
  settings: Settings; onSave: (s: Settings) => void; onClose: () => void;
  updater?: UpdateController;
}) {
  const [s, setS] = useState(settings);
  const [copied, setCopied] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  useEscapeClose(zoomed ? () => setZoomed(false) : onClose);

  const copyUpi = async () => {
    try { await navigator.clipboard.writeText(DONATE.upiId); } catch { /* clipboard blocked */ }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const browse = async () => {
    const p = await pickFolder(s.dest);
    if (p) setS({ ...s, dest: p });
  };

  return (
    <div className="overlay" role="dialog" aria-label="Settings" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">
          <h3>Settings</h3>
          <button className="close" aria-label="close" onClick={onClose}>✕</button>
        </div>
        <div className="settings-fields">
          <label>Default library folder
            <span className="dest-row">
              <input value={s.dest} onChange={(e) => setS({ ...s, dest: e.target.value })} />
              {isTauri() && (
                <button type="button" className="browse" onClick={browse}>Browse…</button>
              )}
            </span>
          </label>
          <label className="field-years">Default years
            <input type="number" min={1} max={25} value={s.years}
              onChange={(e) => setS({ ...s, years: Number(e.target.value) })} /></label>
          <label className="toggle-row">
            <span className="toggle-label">Open folder when done</span>
            <input type="checkbox" checked={s.openWhenDone}
              onChange={(e) => setS({ ...s, openWhenDone: e.target.checked })} />
          </label>
          <label className="toggle-row">
            <span className="toggle-label">Get pre-release updates
              <span className="cat-sub">Be first to try new versions before they roll out to everyone.</span>
            </span>
            <input type="checkbox" checked={s.beta}
              onChange={(e) => setS({ ...s, beta: e.target.checked })} />
          </label>
        </div>
        <button className="primary settings-save" onClick={() => { onSave(s); onClose(); }}>Save</button>
        <section className="support">
          <h4>Support FilingForge</h4>
          <p className="warm">FilingForge is free and open-source, and always will be. If it earns a place in your research, your support keeps it growing — entirely optional.</p>
          <img className="qr" src="/upi.png" alt="UPI QR — scan to support" width={180} height={180}
            role="button" tabIndex={0} title="Click to enlarge"
            onClick={() => setZoomed(true)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setZoomed(true); }} />
          <p className="qr-note">{DONATE.upiNote}</p>
          <button className="btn upi-copy" onClick={copyUpi}>
            {copied ? "Copied ✓" : "Copy UPI ID"}
          </button>
        </section>
        <div className="settings-version">
          <span className="sv-name">FilingForge v{APP_VERSION}</span>
          {updater && (
            <button type="button" className="sv-check"
              disabled={updater.state.phase === "checking"}
              onClick={updater.checkNow}>
              {updater.state.phase === "checking" ? "Checking…" : "Check for updates"}
            </button>
          )}
          {updater?.state.phase === "uptodate" && <span className="sv-note">You're on the latest version ✓</span>}
          {updater?.state.phase === "error" && <span className="sv-note">Couldn't check — try again.</span>}
          {updater?.state.phase === "available" && (
            <button type="button" className="sv-install"
              onClick={() => { void updater.install(); onClose(); }}>
              Update to {updater.state.version} &amp; restart
            </button>
          )}
        </div>
        {zoomed && (
          <div className="qr-zoom" role="dialog" aria-label="UPI QR enlarged" onClick={() => setZoomed(false)}>
            <img src="/upi.png" alt="UPI QR — scan to support" />
          </div>
        )}
      </div>
    </div>
  );
}
