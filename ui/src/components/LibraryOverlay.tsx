import { useEffect, useState } from "react";
import { getLibrary } from "../api";
import type { LibraryItem } from "../types";
export function LibraryOverlay({ root, onOpen, onClose }: {
  root: string; onOpen: (ticker: string) => void; onClose: () => void;
}) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { getLibrary(root).then(setItems).catch((e) => setErr((e as Error).message)); }, [root]);
  return (
    <div className="overlay" role="dialog" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <button className="close" aria-label="close" onClick={onClose}>✕</button>
        <h3>Your library</h3>
        {err && <div className="error-inline">{err}</div>}
        <ul className="lib-list">
          {items.map((it) => (
            <li key={it.ticker}>
              <span className="t">{it.ticker}</span>
              <span className="n">{it.total} docs</span>
              <button className="link" onClick={() => onOpen(it.ticker)}>open folder ▸</button>
            </li>
          ))}
        </ul>
        <p className="dim">A master INDEX.md at the library root maps everything for your AI.</p>
      </div>
    </div>
  );
}
