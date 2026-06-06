import { useEffect, useState } from "react";
import { useEscapeClose } from "../lib/useEscapeClose";
import { getLibrary, getSkills, importSkill } from "../api";
import { pickSkillFile } from "../lib/pickSkillFile";
import type { LibraryItem, ImportedSkill } from "../types";
import bmBrief from "../skills/business-model-brief.md?raw";

// A Skill is just a Markdown prompt the user runs in their OWN Claude / Codex —
// FilingForge never calls an LLM. Two shelves feed this list:
//   • BUILT_IN — packs bundled in the app (free).
//   • imported — *.md the user drops into ~/.filingforge/skills/ (how PREMIUM packs,
//     sold later as a paid download, arrive). The run-flow is identical for both, so
//     adding paid skills later is purely additive — nothing here has to change.
// "Use" asks which downloaded company to run it for, then copies a prompt with that
// company's exact paths pre-filled. Future paid-but-not-owned packs show "Coming soon"
// (later a Buy link); once imported they become "Use" like any other.
type Skill = {
  id: string; name: string; desc: string;
  tier: "Free" | "Premium";
  status: "ready" | "soon";
  prompt?: string;               // present for runnable packs
  imported?: boolean;
};

const BUILT_IN: Skill[] = [
  { id: "bm", name: "Business Model Brief", tier: "Free", status: "ready", prompt: bmBrief,
    desc: "A cited, analyst-grade business-model brief — revenue, concentration, unit economics and moat — rendered to a clean PDF by your own AI." },
  { id: "concall", name: "Concall Brief", tier: "Free", status: "soon",
    desc: "Every earnings call across your library, distilled to the signal — guidance, surprises and what management is really saying." },
  { id: "dd", name: "Full Due-Diligence Report", tier: "Premium", status: "soon",
    desc: "The complete deep-dive: business, financials, balance-sheet forensics, management quality and risks — a finished research report." },
];

// Compose the company-specific prompt: the Skill body, prefixed with the exact paths
// to THIS company's folder + INDEX and the master index, so the user's AI can start
// reading immediately instead of asking where the files are.
function promptFor(skill: Skill, ticker: string, root: string): string {
  const r = root.replace(/\/+$/, "");   // no trailing slash
  return (
    `Run the "${skill.name}" Skill below for ${ticker}, using my local FilingForge library.\n` +
    `Library root: ${r}\n` +
    `${ticker}'s folder: ${r}/${ticker}/\n` +
    `Read its index first: ${r}/${ticker}/INDEX.md\n` +
    `Other companies I have: ${r}/INDEX.md\n` +
    `Report template (use its house style): ${r}/_filingforge-report.md\n` +
    `Work only from ${ticker}'s official filings — the path is above, don't ask me for it.\n\n` +
    `---\n\n` +
    (skill.prompt ?? "")
  );
}

const asSkill = (s: ImportedSkill): Skill => ({
  id: `imported:${s.id}`, name: s.name, desc: s.desc, tier: s.tier,
  status: "ready", prompt: s.prompt, imported: true,
});

export function SkillsOverlay({ root, onClose }: { root: string; onClose: () => void }) {
  const [companies, setCompanies] = useState<LibraryItem[]>([]);
  const [imported, setImported] = useState<ImportedSkill[]>([]);
  const [pickFor, setPickFor] = useState<string | null>(null);   // skill id whose company picker is open
  const [pickQuery, setPickQuery] = useState("");                // filter for the open picker (large libraries)
  const [emptyFor, setEmptyFor] = useState<string | null>(null); // skill id showing the "download first" hint
  const [gotId, setGotId] = useState<string | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);
  useEscapeClose(onClose);

  useEffect(() => { getLibrary(root).then(setCompanies).catch(() => setCompanies([])); }, [root]);
  const refreshSkills = () => getSkills().then(setImported).catch(() => setImported([]));
  useEffect(() => { refreshSkills(); }, []);

  const skills: Skill[] = [...BUILT_IN, ...imported.map(asSkill)];

  // "Use": no library yet → nudge to download a company; otherwise open the picker.
  const use = (s: Skill) => {
    if (!s.prompt) return;
    setGotId(null);
    if (companies.length === 0) { setEmptyFor(s.id); setPickFor(null); return; }
    setEmptyFor(null);
    setPickQuery("");
    setPickFor((cur) => (cur === s.id ? null : s.id));
  };

  // Company chosen → copy the company-specific prompt and confirm.
  const pick = async (s: Skill, ticker: string) => {
    try { await navigator.clipboard.writeText(promptFor(s, ticker, root)); } catch { /* clipboard blocked */ }
    setPickFor(null);
    setGotId(s.id);
    setTimeout(() => setGotId((cur) => (cur === s.id ? null : cur)), 3000);
  };

  // Import a skill .md the user downloaded (e.g. a bought premium pack) → it joins the list.
  const doImport = async () => {
    setImportErr(null);
    const path = await pickSkillFile();
    if (!path) return;                    // cancelled or web build
    try { await importSkill(path); await refreshSkills(); }
    catch (e) { setImportErr((e as Error).message); }
  };

  return (
    <div className="overlay" role="dialog" aria-label="Skills" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">
          <h3>Skills</h3>
          <button className="close" aria-label="close" onClick={onClose}>✕</button>
        </div>
        <p className="skills-pitch">
          Skills turn your clean library into finished work. Pick a pack and the
          company to run it for — FilingForge fills in the exact paths, you paste
          it into the Claude desktop app or Codex, and your AI produces the result.
          Nothing leaves your machine.
        </p>

        <ul className="skill-list">
          {skills.map((s) => {
            const got = gotId === s.id;
            const premium = s.tier === "Premium";
            const picking = pickFor === s.id;
            return (
              <li key={s.id} className={"skill-row" + (s.status === "soon" ? " soon" : "")}>
                <div className="pr-main">
                  <div className="pr-head"><span className="pr-name">{s.name}</span></div>
                  <p className="pr-desc">{s.desc}</p>
                </div>
                <div className="pr-buy">
                  <span className={"pr-price" + (premium ? " premium" : " free")}>{s.tier}</span>
                  {s.status === "ready"
                    ? <button className="pr-get" onClick={() => use(s)}>{got ? "Copied ✓" : "Use"}</button>
                    : <span className="pr-comingsoon">Coming soon</span>}
                </div>

                {picking && (() => {
                  // Big libraries (100s of tickers) get a search box; click = auto-copy, no extra OK.
                  const q = pickQuery.trim().toLowerCase();
                  const shown = q ? companies.filter((c) => c.ticker.toLowerCase().includes(q)) : companies;
                  return (
                    <div className="pr-pick">
                      <span className="pr-pick-label">Run it for which company?</span>
                      {companies.length > 8 && (
                        <input className="pr-pick-search" type="search" autoFocus
                          placeholder={`Search ${companies.length} companies…`}
                          value={pickQuery} onChange={(e) => setPickQuery(e.target.value)}
                          aria-label="Find a company" />
                      )}
                      <div className="pr-pick-list">
                        {shown.map((c) => (
                          <button key={c.ticker} className="pr-pick-co" onClick={() => pick(s, c.ticker)}>
                            {c.ticker}
                          </button>
                        ))}
                      </div>
                      {q && !shown.length && <span className="pr-pick-empty">No company matches “{pickQuery.trim()}”.</span>}
                    </div>
                  );
                })()}
                {emptyFor === s.id && (
                  <p className="pr-empty-note">
                    Download a company first — then Use builds a ready-to-run prompt with its exact paths.
                  </p>
                )}
                {got && (
                  <p className="pr-got-note">
                    Prompt copied — paste it into the Claude desktop app or Codex and let it run. The paths are already filled in.
                  </p>
                )}
              </li>
            );
          })}
        </ul>

        <div className="skills-import">
          <button className="link" onClick={doImport}>+ Import a skill…</button>
          <span className="skills-import-hint">Add a skill you downloaded — it lives in your library and survives reinstalls.</span>
          {importErr && <p className="error-inline">{importErr}</p>}
        </div>
      </div>
    </div>
  );
}
