// Crisp ~20px inline SVG icons, currentColor so hover ember color works.
const ICON = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const, "aria-hidden": true };

const LibraryIcon = () => (
  <svg {...ICON}>
    <rect x="3" y="4" width="4" height="16" rx="1" />
    <rect x="9" y="4" width="4" height="16" rx="1" />
    <path d="M15.5 5.2l3.4-.9 2 14.4-3.4.9z" />
  </svg>
);
const SkillsIcon = () => (
  <svg {...ICON}>
    <path d="M10 4h4v2.2a1.8 1.8 0 1 0 3.6 0V6H20v3.4h-.2a1.8 1.8 0 1 0 0 3.6h.2V20h-3.4v-.2a1.8 1.8 0 1 0-3.6 0v.2H10v-3.4a1.8 1.8 0 1 0-3.6 0H4V13a1.8 1.8 0 1 0 0-3.6V6h3.4v.2a1.8 1.8 0 1 0 3.6 0z" />
  </svg>
);
const SettingsIcon = () => (
  <svg {...ICON}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);
const BugIcon = () => (
  <svg {...ICON}>
    <path d="M9.5 7 8 4.5M14.5 7 16 4.5" />
    <rect x="6.5" y="7" width="11" height="13" rx="5.5" />
    <path d="M12 7.5v11.5" />
    <path d="M6.5 11 3 9.5M17.5 11 21 9.5M6.2 14H2.5M17.8 14h3.7M6.5 17 3 18.8M17.5 17 21 18.8" />
  </svg>
);

function IconButton({ label, onClick, children }: {
  label: string; onClick: () => void; children: React.ReactNode;
}) {
  return (
    <button className="tb-icon" aria-label={label} onClick={onClick}>
      {children}
      <span className="tb-tip" aria-hidden="true">{label}</span>
    </button>
  );
}

export function TitleBar({ onSettings, onLibrary, onSkills, onReport, showLibrary, showWordmark }: {
  onSettings: () => void; onLibrary: () => void; onSkills: () => void;
  onReport: () => void; showLibrary: boolean; showWordmark: boolean;
}) {
  return (
    <div className="titlebar">
      {showWordmark
        ? <span className="wordmark">FilingForge<span className="wm-dot">.</span></span>
        : <span className="wordmark-spacer" aria-hidden="true" />}
      <nav className="actions">
        {showLibrary && (
          <IconButton label="Library" onClick={onLibrary}><LibraryIcon /></IconButton>
        )}
        <IconButton label="Skills" onClick={onSkills}><SkillsIcon /></IconButton>
        <IconButton label="Settings" onClick={onSettings}><SettingsIcon /></IconButton>
        <IconButton label="Report a bug" onClick={onReport}><BugIcon /></IconButton>
      </nav>
    </div>
  );
}
