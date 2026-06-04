import type { Candidate } from "../types";

export function ResultsDropdown({ items, activeIndex, onPick }: {
  items: Candidate[]; activeIndex: number; onPick: (c: Candidate) => void;
}) {
  if (!items.length) return null;
  return (
    <ul className="dropdown" role="listbox">
      {items.map((c, i) => (
        <li key={c.scrip_code} id={`opt-${c.scrip_code}`} role="option"
            aria-selected={i === activeIndex}
            className={"dropdown-row" + (i === activeIndex ? " active" : "")}
            onMouseDown={(e) => { e.preventDefault(); onPick(c); }}>
          <span className="code">[{c.scrip_code}]</span>
          <span className="name">{c.company}</span>
          {c.isin && <span className="isin">{c.isin}</span>}
          {c.is_primary && <span className="primary">● primary</span>}
        </li>
      ))}
    </ul>
  );
}
