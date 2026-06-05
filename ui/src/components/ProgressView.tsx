import type { ProgressEvent } from "../types";

// Friendlier copy than the raw stage keys — the user is watching this scroll by, so it
// should read like the app is thinking, not dumping verbs.
const PHASES: Record<string, string> = {
  resolve: "Finding filings on BSE",
  search: "Finding filings on BSE",
  download: "Gathering filings",
  convert: "Converting to clean Markdown",
  index: "Building your index",
};
function phaseLabel(stage?: string): string {
  return (stage && PHASES[stage]) || "Working";
}

// A word for where we are, highlighted at the % milestones.
function milestone(pct: number): string {
  if (pct >= 100) return "Done";
  if (pct >= 75) return "Almost there";
  if (pct >= 50) return "Over halfway";
  if (pct >= 25) return "Underway";
  if (pct > 0) return "Getting going";
  return "Starting up";
}

export function ProgressView({ progress, log, onBack }: {
  progress: ProgressEvent | null; log: string[]; onBack: () => void;
}) {
  const p = progress;
  const pct = p?.percent ?? 0;
  const feed = p ? log.filter((l) => l !== p.message) : log;
  const stageText = p ? phaseLabel(p.stage) : "Finding filings on BSE";

  return (
    <div className="building">
      <button className="back" onClick={onBack}>‹ Back</button>

      <div className="prog-stage" aria-live="polite">{stageText}</div>
      <div className="prog-pct">{pct}%</div>
      <div className={"prog-milestone" + (pct >= 100 ? " done" : "")}>{milestone(pct)}</div>

      <div className="bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="fill" style={{ width: `${pct}%` }} />
      </div>

      {p && (
        <div className="prog-item">
          <span className="pi-name">{p.message}</span>
          {p.total > 0 && <span className="pi-count">{p.current} of {p.total}</span>}
        </div>
      )}

      <ul className="log" aria-hidden="true">{feed.slice(-6).map((l, i) => <li key={i}>&gt; {l}</li>)}</ul>
    </div>
  );
}
