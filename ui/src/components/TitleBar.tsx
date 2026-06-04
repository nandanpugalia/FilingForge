import { ISSUES_URL } from "../config";
export function TitleBar({ onSettings, onLibrary, showLibrary }: {
  onSettings: () => void; onLibrary: () => void; showLibrary: boolean;
}) {
  return (
    <div className="titlebar">
      <span className="wordmark">FilingForge</span>
      <div className="actions">
        {showLibrary && <button className="lib-open" onClick={onLibrary}>▤ Library</button>}
        <button className="gear" aria-label="settings" onClick={onSettings}>⚙</button>
        <a className="bug" href={ISSUES_URL} target="_blank" rel="noreferrer">report a bug ↗</a>
      </div>
    </div>
  );
}
