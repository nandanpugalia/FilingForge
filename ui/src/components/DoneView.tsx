import { useState } from "react";
import type { BuildResult, PendingDocument } from "../types";
import { PendingDocuments } from "./PendingDocuments";

// Folder-slug → friendly label (slugs come from the engine's library counts).
const FOLDER_LABELS: Record<string, string> = {
  "annual-reports": "Annual reports",
  "company-update": "Company updates",
  "agm-egm": "AGM / EGM",
  "board-meeting": "Board meetings",
  "corp-action": "Corp actions",
  "investor-ppts": "Investor presentations",
  "concalls": "Concalls",
  "quarterly": "Financial results",
  "press": "Press releases",
  "analyst-meets": "Analyst meets",
  "insider-trading-sast": "Insider trading",
  "others": "Other filings",
};

function labelFor(slug: string): string {
  if (FOLDER_LABELS[slug]) return FOLDER_LABELS[slug];
  // titleize an unknown slug: "some-thing" → "Some thing"
  const words = slug.replace(/[-_]+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : slug;
}

export function DoneView({ ticker, name, dest, result, breakdown, onOpen, onReset,
  onOpenPendingSource, onUsePendingPdf, importingPendingId, pendingErrors }: {
  ticker: string; name?: string; dest?: string; result: BuildResult;
  breakdown?: Record<string, number>; onOpen: () => void; onReset: () => void;
  onOpenPendingSource?: (item: PendingDocument) => void;
  onUsePendingPdf?: (item: PendingDocument) => void;
  importingPendingId?: string | null;
  pendingErrors?: Record<string, string>;
}) {
  const [copied, setCopied] = useState(false);
  const skipNote = result.skipped ? ` · ${result.skipped} had no attached PDF` : "";
  const failNote = result.failed ? ` · ${result.failed} failed` : "";
  const pending = result.pending ?? [];
  const hasPending = pending.length > 0;
  const ready = result.ready ?? result.downloaded;
  const rows = breakdown
    ? Object.entries(breakdown).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])
    : [];

  const root = dest ?? ".";
  const promptText =
    `I've built a local filings library for ${name || ticker}.\n` +
    `Read its index first:  ${root}/${ticker}/INDEX.md\n` +
    `Then answer from its official filings. Other companies I have: ${root}/INDEX.md`;

  const copyPrompt = () => {
    navigator.clipboard.writeText(promptText).then(
      () => { setCopied(true); setTimeout(() => setCopied(false), 2000); },
      () => {},
    );
  };
  return (
    <div className="done">
      <h2 className="ready">{result.cancelled
        ? `Stopped — your ${name || ticker} library was saved.`
        : hasPending
          ? `Your ${name || ticker} library is almost ready.`
          : `Your ${name || ticker} library is ready.`}</h2>
      <div className="saved-as">Saved in the <code>{ticker}/</code> folder</div>
      <div className="summary">
        {hasPending
          ? `${ready} document${ready === 1 ? "" : "s"} ready · ${pending.length} awaiting source PDF${pending.length === 1 ? "" : "s"}`
          : <>{result.cancelled && "Stopped early — "}{result.downloaded} document{result.downloaded === 1 ? "" : "s"} added{skipNote}{failNote}</>}
        {result.cancelled && " · everything saved is complete and indexed"}
      </div>
      {rows.length > 0 && (
        <div className="breakdown">
          <div className="breakdown-head">By type:</div>
          <ul className="breakdown-list">
            {rows.map(([slug, n]) => (
              <li key={slug}>
                <span className="bd-count">{n}</span>
                <span className="bd-label">{labelFor(slug)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {hasPending && <PendingDocuments items={pending}
        importingId={importingPendingId ?? null} errors={pendingErrors ?? {}}
        onOpenSource={onOpenPendingSource ?? (() => {})}
        onUsePdf={onUsePendingPdf ?? (() => {})} />}
      {!hasPending && <div className="ai-hook">An INDEX.md sits in the folder — point the Claude desktop app or Codex at it to read the entire company.</div>}
      {!hasPending && <div className="ai-prompt">
        <div className="ai-prompt-head">
          <span className="ai-prompt-label">Paste this to your AI ↓</span>
          <button type="button" className="ai-prompt-copy" onClick={copyPrompt}>
            {copied ? "Copied ✓" : "Copy"}
          </button>
        </div>
        <pre className="ai-prompt-body">{promptText}</pre>
      </div>}
      <button className="primary" onClick={onOpen}>Open folder ▸</button>
      <button className="link" onClick={onReset}>‹ Back to home</button>
    </div>
  );
}
