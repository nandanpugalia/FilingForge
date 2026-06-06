import { useEffect, useState } from "react";
import { getLibrary } from "../api";
import type { LibraryItem } from "../types";
import { useEscapeClose } from "../lib/useEscapeClose";
export function LibraryOverlay({ root, onOpen, onRefresh, onAddCompany, onOpenReport, onClose }: {
  root: string; onOpen: (ticker: string) => void; onRefresh: (ticker: string) => void;
  onAddCompany: () => void; onOpenReport?: (reportRel: string) => void; onClose: () => void;
}) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  useEscapeClose(onClose);
  useEffect(() => { getLibrary(root).then(setItems).catch((e) => setErr((e as Error).message)); }, [root]);
  // search only earns its place once the list is long enough to scroll
  const showSearch = items.length > 8;
  const q = query.trim().toLowerCase();
  const shown = q ? items.filter((it) => it.ticker.toLowerCase().includes(q)) : items;
  return (
    <div className="overlay" role="dialog" aria-label="Your library" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">
          <h3>Your library</h3>
          <button className="close" aria-label="close" onClick={onClose}>✕</button>
        </div>
        {showSearch && (
          <input className="lib-search" type="search" autoFocus
            placeholder={`Search ${items.length} companies…`}
            value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search your library" />
        )}
        {err && <div className="error-inline">{err}</div>}
        <ul className="lib-list">
          {shown.map((it) => (
            <li key={it.ticker}>
              <span className="t">{it.ticker}</span>
              <span className="n">{it.total} docs</span>
              <span className="lib-actions">
                <button className="link" onClick={() => onRefresh(it.ticker)} title="Pull new filings">Refresh ↻</button>
                {it.hasReport && it.reportRel && onOpenReport && (
                  <button className="link" onClick={() => onOpenReport(it.reportRel!)}>open report ▸</button>
                )}
                <button className="link" onClick={() => onOpen(it.ticker)}>open folder ▸</button>
              </span>
            </li>
          ))}
        </ul>
        {q && !shown.length && <p className="dim lib-empty">No company matches “{query.trim()}”.</p>}
        <button className="btn lib-add" onClick={onAddCompany}>+ Add company</button>
        <p className="dim">A master INDEX.md at the library root maps everything for your AI.</p>
      </div>
    </div>
  );
}
