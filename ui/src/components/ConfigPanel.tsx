import { useState } from "react";
import type { Candidate, BuildScope, Settings, PreviewResult } from "../types";
import { CATEGORIES, DEFAULT_CURATED } from "../categories";
import { tickerFor } from "../lib/ticker";
import { previewBuild } from "../api";

export function ConfigPanel({ company, settings, starting, onChangeCompany, onBuild }: {
  company: Candidate; settings: Settings; starting: boolean;
  onChangeCompany: () => void; onBuild: (s: BuildScope) => void;
}) {
  const [years, setYears] = useState(settings.years);
  const [everything, setEverything] = useState(settings.everything);
  const [picked, setPicked] = useState<string[]>(settings.categories.length ? settings.categories : DEFAULT_CURATED);
  // Preview-before-download: clicking Build first shows how many filings this scope would
  // pull (with a per-category breakdown) so a 5-year "everything" pull can't start blind.
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewErr, setPreviewErr] = useState<string | null>(null);
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

  async function doPreview() {
    setPreviewErr(null); setPreviewing(true);
    try { setPreview(await previewBuild(scope())); }
    catch (e) { setPreviewErr((e as Error).message); }
    finally { setPreviewing(false); }
  }

  // ── Confirm step: show the count + breakdown, let the user approve or go back ──
  if (preview) {
    return (
      <div className="config preview-confirm">
        <button className="back" onClick={() => setPreview(null)}>‹ Adjust</button>
        <div className="company-header">
          <span className="name">{company.company}</span>
          <span className="code">[{company.scrip_code}]</span>
        </div>
        <div className="preview-head">
          <span className="preview-count">{preview.new}</span>
          <span className="preview-label">new filing{preview.new === 1 ? "" : "s"} to download</span>
        </div>
        <div className="preview-sub">
          {preview.total} found over {yLabel}
          {preview.have > 0 && <> · {preview.have} already in your library</>}
        </div>
        <ul className="preview-breakdown">
          {preview.by_category.map(c => (
            <li key={c.label}><span className="pb-label">{c.label}</span><span className="pb-count">{c.count}</span></li>
          ))}
        </ul>
        <div className="preview-actions">
          <button className="primary" disabled={starting || preview.new === 0}
            onClick={() => onBuild(scope())}>
            {preview.new === 0 ? "Nothing new to download" : `Download ${preview.new} ▸`}
          </button>
          <button className="link" onClick={() => setPreview(null)}>Adjust scope</button>
        </div>
      </div>
    );
  }

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
        All filings <span className="cat-sub">(more, but noisier — incl. notices &amp; ballots)</span>
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
      {previewErr && <p className="error-inline">{previewErr}</p>}
      <button className="primary" disabled={starting || previewing || (!everything && picked.length === 0)}
        onClick={doPreview}>
        {previewing ? "Checking…" : <>Build library ▸<span className="helper">preview first · then download</span></>}
      </button>
    </div>
  );
}
