import { useState } from "react";
import type { Candidate, BuildScope, Settings } from "../types";
import { CATEGORIES, DEFAULT_CURATED } from "../categories";
import { tickerFor } from "../lib/ticker";

export function ConfigPanel({ company, dest, settings, starting, onChangeCompany, onDestChange, onBuild }: {
  company: Candidate; dest: string; settings: Settings; starting: boolean;
  onChangeCompany: () => void; onDestChange: (dest: string) => void; onBuild: (s: BuildScope) => void;
}) {
  const [years, setYears] = useState(settings.years);
  const [everything, setEverything] = useState(settings.everything);
  const [picked, setPicked] = useState<string[]>(settings.categories.length ? settings.categories : DEFAULT_CURATED);
  const ticker = tickerFor(company);

  const toggle = (key: string) => setPicked(p => p.includes(key) ? p.filter(k => k !== key) : [...p, key]);
  const scope = (): BuildScope => ({
    scrip_code: company.scrip_code, ticker, dest, years,
    everything, categories: everything ? [] : picked,
  });
  const yLabel = `${years} year${years > 1 ? "s" : ""}`;
  const scopeLine = everything
    ? `≈ ${yLabel} · everything · ${dest}`
    : `≈ ${yLabel} · ${picked.length} type${picked.length === 1 ? "" : "s"} · ${dest}`;

  return (
    <div className="config">
      <div className="company-header">
        <span className="name">{company.company}</span>
        <span className="code">[{company.scrip_code}]</span>
        <button className="link" onClick={onChangeCompany}>change ✕</button>
      </div>

      <label className="years">How many years back?
        <button aria-label="fewer years" onClick={() => setYears(y => Math.max(1, y - 1))}>−</button>
        <span className="years-val">{years}</span>
        <button aria-label="more years" onClick={() => setYears(y => Math.min(25, y + 1))}>+</button>
      </label>

      <label className="everything-toggle">
        <input type="checkbox" checked={everything} onChange={() => setEverything(e => !e)} />
        Everything — all filings
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

      <label className="dest-row">Destination
        <input value={dest} onChange={(e) => onDestChange(e.target.value)} />
      </label>

      <div className="scope-line">{scopeLine}</div>
      <button className="primary" disabled={starting} onClick={() => onBuild(scope())}>
        Get the filings ▸<span className="helper">downloads · cleans · indexes</span>
      </button>
    </div>
  );
}
