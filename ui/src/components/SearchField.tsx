import { useEffect, useRef, useState } from "react";
import { resolve } from "../api";
import { SEARCH_DEBOUNCE_MS } from "../config";
import type { Candidate } from "../types";
import { ResultsDropdown } from "./ResultsDropdown";

export function SearchField({ onPick }: { onPick: (c: Candidate) => void }) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Candidate[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) { setItems([]); setErr(null); setLoading(false); return; }
    setLoading(true);
    const id = ++reqId.current;
    timer.current = setTimeout(async () => {
      try {
        const r = await resolve(q.trim());
        if (id !== reqId.current) return;           // ignore stale responses
        setItems(r); setErr(null); setActive(0);
      } catch (e) {
        if (id !== reqId.current) return;
        setItems([]); setErr((e as Error).message);
      } finally { if (id === reqId.current) setLoading(false); }
    }, SEARCH_DEBOUNCE_MS);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [q]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!items.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(a => Math.min(items.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive(a => Math.max(0, a - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); onPick(items[active]); }
    else if (e.key === "Escape") { setItems([]); setErr(null); }
  };

  const showNoMatch = !loading && !err && q.trim().length >= 2 && items.length === 0;

  return (
    <div className="search">
      <span className="prompt">&gt;</span>
      <input className="search-input" value={q} autoFocus
        placeholder="Look up a company"
        aria-activedescendant={items[active] ? `opt-${items[active].scrip_code}` : undefined}
        onChange={(e) => setQ(e.target.value)} onKeyDown={onKeyDown} />
      {err && <div className="error-inline">{err}</div>}
      {showNoMatch && <div className="no-match">No company found.</div>}
      <ResultsDropdown items={items} activeIndex={active} onPick={onPick} />
    </div>
  );
}
