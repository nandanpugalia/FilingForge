import { useState } from "react";
import type { Candidate, BuildScope, Settings } from "../types";
import { CATEGORIES, DEFAULT_CURATED } from "../categories";
import { tickerFor } from "../lib/ticker";

export function ConfigPanel({ company, settings, starting, onChangeCompany, onBuild }: {
  company: Candidate; settings: Settings; starting: boolean;
  onChangeCompany: () => void; onBuild: (s: BuildScope) => void;
}) {
  const [years, setYears] = useState(settings.years);
  const [everything, setEverything] = useState(settings.everything);
  const [picked, setPicked] = useState<string[]>(settings.categories.length ? settings.categories : DEFAULT_CURATED);
  const ticker = tickerFor(company);

  const toggle = (key: string) => setPicked(p => p.includes(key) ? p.filter(k => k !== key) : [...p, key]);
  // Destination is the single global library folder (set at first run, changed in
  // Settings) — never chosen per build, so the library view can't diverge from it.
  const scope = (): BuildScope => ({
    scrip_code: company.scrip_code, ticker, dest: settings.dest, years,
    everything, categories: everything ? [] : picked,
  });
  const yLabel = `${years} year${years > 1 ? "s" : ""}`;
  const scopeLine = everything
    ? `${yLabel} · all filings · ${settings.dest}`
    : `${yLabel} · ${picked.length} type${picked.length === 1 ? "" : "s"} · ${settings.dest}`;

  return (
    <div className="config">
      <button className="back" onClick={onChangeCompany}>‹ Back</button>
      <div className="company-header">
        <span className="name">{company.company}</span>
        <span className="code">[{company.scrip_code}]</span>
        <button className="link" onClick={onChangeCompany}>Change ✕</button>
      </div>

      <label className="years">Years of history
        <button aria-label="fewer years" onClick={() => setYears(y => Math.max(1, y - 1))}>−</button>
        <span className="years-val">{years}</span>
        <button aria-label="more years" onClick={() => setYears(y => Math.min(25, y + 1))}>+</button>
      </label>

      <label className="everything-toggle">
        <input type="checkbox" checked={everything} onChange={() => setEverything(e => !e)} />
        All filings
      </label>

      {!everything && (
        <ul className="checklist">
          {CATEGORIES.map(c => (
            <li key={c.key}>
              <label>
                <input type="checkbox" checked={picked.includes(c.key)} onChange={() => toggle(c.key)} />
                <span className="cat-label">{c.label}</span>
                <span className="cat-sub">{c.sublabel}</span>
              </label>
            </li>
          ))}
        </ul>
      )}

      <div className="scope-line">{scopeLine}</div>
      <button className="primary" disabled={starting} onClick={() => onBuild(scope())}>
        Build library ▸<span className="helper">download · convert · index</span>
      </button>
    </div>
  );
}
