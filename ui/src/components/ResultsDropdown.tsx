import { useEffect, useRef } from "react";
import type { Candidate } from "../types";

export function ResultsDropdown({ items, activeIndex, onPick }: {
  items: Candidate[]; activeIndex: number; onPick: (c: Candidate) => void;
}) {
  const activeRef = useRef<HTMLLIElement>(null);
  // keep the keyboard-highlighted row visible as you arrow through a long list
  useEffect(() => { activeRef.current?.scrollIntoView({ block: "nearest" }); }, [activeIndex]);
  if (!items.length) return null;
  return (
    <ul className="dropdown" role="listbox">
      {items.map((c, i) => (
        <li key={c.scrip_code} id={`opt-${c.scrip_code}`} role="option"
            ref={i === activeIndex ? activeRef : null}
            aria-selected={i === activeIndex}
            className={"dropdown-row" + (i === activeIndex ? " active" : "")}
            onMouseDown={(e) => { e.preventDefault(); onPick(c); }}>
          <span className="code">[{c.scrip_code}]</span>
          <span className="name">{c.company}</span>
          {c.isin && <span className="isin">{c.isin}</span>}
        </li>
      ))}
    </ul>
  );
}
