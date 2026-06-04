import type { ProgressEvent } from "../types";
export function ProgressView({ progress, log, onCancel }: {
  progress: ProgressEvent | null; log: string[]; onCancel: () => void;
}) {
  const p = progress; const pct = p?.percent ?? 0;
  const feed = p ? log.filter((l) => l !== p.message) : log;
  return (
    <div className="building">
      <div className="current" aria-live="polite">{p ? p.message : "Finding filings on BSE…"}</div>
      <div className="bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="meta">
        <span className="pct">{pct}%</span>
        {p && p.total > 0 && <span className="count">{p.current} of {p.total}</span>}
      </div>
      <ul className="log" aria-hidden="true">{feed.slice(-6).map((l, i) => <li key={i}>&gt; {l}</li>)}</ul>
      <button className="link" onClick={onCancel}>Cancel</button>
    </div>
  );
}
