import type { BuildResult } from "../types";
export function DoneView({ ticker, result, onOpen, onReset }: {
  ticker: string; result: BuildResult; onOpen: () => void; onReset: () => void;
}) {
  const skipNote = result.skipped ? ` (${result.skipped} had no attached PDF)` : "";
  return (
    <div className="done">
      <h2 className="ready">Your {ticker} library is ready.</h2>
      <div className="summary">{result.downloaded} documents added · {result.skipped} skipped{skipNote} · {result.failed} failed</div>
      <div className="ai-hook">INDEX.md written — point ChatGPT or Claude at this folder and it can read the whole company.</div>
      <button className="primary" onClick={onOpen}>Open folder ▸</button>
      <button className="link" onClick={onReset}>‹ build another</button>
    </div>
  );
}
