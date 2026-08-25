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
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const pending = result.pending ?? [];
  const hasPending = pending.length > 0;
  const ready = result.ready ?? result.downloaded;
  const rows = breakdown
    ? Object.entries(breakdown).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])
    : [];

  const root = (dest ?? ".").replace(/[\\/]+$/, "") || ".";
  const promptText =
    `I've built a local filings library for ${name || ticker}.\n` +
    `Read its index first: ${root}/${ticker}/INDEX.md\n` +
    `Use only the official filings in that library and cite the filenames you rely on.\n` +
    `Tell me when you've read the index and are ready, then wait for my question.`;

  const runFacts: string[] = [];
  if (result.downloaded) runFacts.push(
    `${result.downloaded} ${result.skipped ? "new" : "added"}`,
  );
  if (result.skipped) runFacts.push(`${result.skipped} already in your library`);
  if (result.failed) runFacts.push(
    `${result.failed} couldn't be added`,
  );

  const filingNoun = (count: number) => `official filing${count === 1 ? "" : "s"}`;
  const readyText = result.cancelled
    ? `${ready} complete ${filingNoun(ready)} ${ready === 1 ? "is" : "are"} ready`
    : hasPending
      ? `${ready} ${filingNoun(ready)} ready`
      : `${ready} ${filingNoun(ready)} ready for your AI`;

  const pendingText = pending.length === 1
    ? "1 needs its source PDF"
    : `${pending.length} need their source PDFs`;

  const copyPrompt = async () => {
    setCopyState("idle");
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(promptText);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setCopyState("error");
    }
  };

  return (
    <div className="done">
      <div className="done-head">
        <h2 className="ready">{result.cancelled
          ? "Saved safely"
          : hasPending ? "Library almost ready" : "Library ready"}</h2>
        <div className="done-company">{name || ticker}</div>
        <div className="done-total">{readyText}</div>
      </div>
      <div className="saved-as">Saved in <code>{ticker}/</code></div>

      {!hasPending && !result.cancelled && <div className="done-actions">
        <button type="button" className="primary" onClick={copyPrompt}>
          {copyState === "copied" ? "Copied ✓" : "Copy AI instructions"}
        </button>
        <button type="button" className="done-open" onClick={onOpen}>Open library</button>
      </div>}
      {copyState === "error" && <div className="copy-error" role="alert">
        Couldn't copy the instructions. Check clipboard permission and try again.
      </div>}

      <div className="summary">
        {hasPending && <span>{pendingText}</span>}
        {hasPending && runFacts.length > 0 && <span> · </span>}
        {runFacts.length > 0 ? runFacts.join(" · ") : !hasPending && "Everything is already up to date"}
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
      {(hasPending || result.cancelled) && <button type="button" className="done-open" onClick={onOpen}>
        Open library
      </button>}
      <button className="link" onClick={onReset}>‹ Back to home</button>
    </div>
  );
}
