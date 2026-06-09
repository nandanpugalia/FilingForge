import { useEffect, useRef, useState } from "react";
import { useEscapeClose } from "../lib/useEscapeClose";
import { getLibrary, getSkills, importSkill, installSkillMd, startCheckout, redeem } from "../api";
import { openExternal } from "../lib/openExternal";
import { setPending, getPending, getPendingUrl, getPendingSkill, clearPending } from "../lib/pendingPurchase";
import { pickSkillFile } from "../lib/pickSkillFile";
import type { LibraryItem, ImportedSkill } from "../types";
import bmBrief from "../skills/business-model-brief.md?raw";

// A Skill is just a Markdown prompt the user runs in their OWN Claude / Codex —
// FilingForge never calls an LLM. Two shelves feed this list:
//   • BUILT_IN — packs bundled in the app (free).
//   • imported — *.md the user drops into ~/.filingforge/skills/ (how PREMIUM packs,
//     sold as a paid download, arrive). The run-flow is identical for both.
// "Use" asks which downloaded company to run it for, then copies a prompt with that
// company's exact paths pre-filled.
//
// Premium: the first paid pack is **Concall Decoder (₹3,000)**. When NOT owned it shows
// a "Get — ₹3,000" buy row (checkout → pay in browser → poll auto-unlocks → install).
// Once owned it arrives in ~/.filingforge/skills/ and is listed by getSkills() with
// id "concall-decoder" — so it renders as a normal "Use" skill and the buy teaser is
// suppressed (dedup), no double-listing.
type Skill = {
  id: string; name: string; desc: string;
  tier: "Free" | "Premium";
  status: "ready" | "soon";
  prompt?: string;               // present for runnable packs
  imported?: boolean;
};

// The paid skills the buy flow sells. CONTENT lives in the Worker (KV), never the repo.
// Add a paid skill = add an entry here (and to the Worker CATALOG + SKILLS KV).
type Premium = { id: string; name: string; desc: string; price: string };
const PREMIUM: Premium[] = [
  {
    id: "concall-decoder", name: "Concall Decoder", price: "₹3,000",
    desc:
      "Every earnings call in your library, decoded — management's guidance track record " +
      "(kept vs missed), shifts in tone, the questions analysts keep pressing, and the ones " +
      "management avoids. A cited read on how much to trust the team.",
  },
  {
    id: "capital-allocation-audit", name: "Capital Allocation Audit", price: "₹3,000",
    desc:
      "A multi-year audit of what management does with the cash — where every rupee of operating " +
      "cash flow went, the return earned on it (ROIC), the acquisition track record, buybacks & " +
      "dilution, leverage, and the red flags. Cited, with a proof-of-work manifest.",
  },
];

const BUILT_IN: Skill[] = [
  { id: "bm", name: "Business Model Brief", tier: "Free", status: "ready", prompt: bmBrief,
    desc: "An analyst-grade brief on what the business really is and how it wins — revenue mix, " +
      "customer concentration, unit economics, and a six-point moat assessment. Every claim cited " +
      "to its filing, rendered as a clean report by your own AI." },
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
    `Report template (use its house style): ${r}/_filingforge/report-template.md\n` +
    `Work only from ${ticker}'s official filings — the path is above, don't ask me for it.\n\n` +
    `---\n\n` +
    (skill.prompt ?? "")
  );
}

const asSkill = (s: ImportedSkill): Skill => ({
  id: `imported:${s.id}`, name: s.name, desc: s.desc, tier: s.tier,
  status: "ready", prompt: s.prompt, imported: true,
});

// Does this imported skill match a paid pack? (id or name, case-insensitive)
const matchesPremium = (s: ImportedSkill, p: Premium): boolean =>
  s.id.toLowerCase() === p.id || s.name.trim().toLowerCase() === p.name.toLowerCase();

export function SkillsOverlay({ root, onClose }: { root: string; onClose: () => void }) {
  const [companies, setCompanies] = useState<LibraryItem[]>([]);
  const [imported, setImported] = useState<ImportedSkill[]>([]);
  const [pickFor, setPickFor] = useState<string | null>(null);   // skill id whose company picker is open
  const [pickQuery, setPickQuery] = useState("");                // filter for the open picker (large libraries)
  const [emptyFor, setEmptyFor] = useState<string | null>(null); // skill id showing the "download first" hint
  const [gotId, setGotId] = useState<string | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);

  // ── Buy-flow state (Concall Decoder) ──────────────────────────────────────
  const [buyBusy, setBuyBusy] = useState(false);                  // checkout in flight
  const [polling, setPolling] = useState(false);                  // poll loop running
  const [buyMsg, setBuyMsg] = useState<string | null>(null);      // status / friendly error
  const [installed, setInstalled] = useState(false);             // toast "added ✓"
  const [installedName, setInstalledName] = useState("Skill");    // which pack the toast names
  const [code, setCode] = useState("");                           // paste-code field
  const [email, setEmail] = useState("");                         // buyer email (receipt + unlock code)
  const [buyingId, setBuyingId] = useState<string | null>(null); // which premium skill's email step is open
  const [resume, setResume] = useState<string | null>(null);     // pending session for the banner
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

  useEscapeClose(onClose);

  useEffect(() => { getLibrary(root).then(setCompanies).catch(() => setCompanies([])); }, [root]);
  const refreshSkills = () => getSkills().then(setImported).catch(() => setImported([]));
  useEffect(() => { refreshSkills(); }, []);

  // Per-skill ownership: a paid pack is "owned" iff an imported skill matches it.
  const isOwned = (p: Premium) => imported.some((s) => matchesPremium(s, p));
  const unowned = PREMIUM.filter((p) => !isOwned(p));
  // The pending purchase's skill (so the resume banner + install name the right pack). A legacy
  // pending with no stored skill id is treated as the first paid pack (back-compat).
  const pendingSkill = getPendingSkill();
  const pendingDef = (pendingSkill.id && PREMIUM.find((p) => p.id === pendingSkill.id)) || PREMIUM[0];
  const pendingOwned = isOwned(pendingDef);

  // Resume banner: a pending session exists AND that skill isn't owned yet.
  useEffect(() => {
    const p = getPending();
    setResume(p && !pendingOwned ? p : null);
    if (pendingOwned) clearPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imported]);

  // Stop the poll loop on unmount.
  useEffect(() => () => { if (pollTimer.current) clearInterval(pollTimer.current); }, []);

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

  // ── Buy flow ──────────────────────────────────────────────────────────────
  const stopPoll = () => { if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null; } setPolling(false); };

  // Install the watermarked md → mark owned → toast → clear pending.
  const install = async (md: string) => {
    // Name it from the md's OWN frontmatter `name:` first — that's authoritative and is the only
    // correct source for a pasted code with no pending (comp codes, cross-device redeems). Fall
    // back to the pending skill, then the first paid pack. Without this, a pasted CAU code would
    // install as "Concall Decoder" and overwrite concall-decoder.md.
    const fmName = md.match(/^---\s*[\s\S]*?\bname:\s*(.+?)\s*$/m)?.[1]?.trim();
    const nm = fmName || getPendingSkill().name || PREMIUM[0].name;
    await installSkillMd(nm, md);
    await refreshSkills();
    clearPending();
    setResume(null);
    setBuyingId(null);
    stopPoll();
    setBuyMsg(null);
    setInstalledName(nm);
    setInstalled(true);
    setTimeout(() => setInstalled(false), 4000);
  };

  // One redeem attempt. Returns true if it installed (so callers can stop).
  const tryRedeem = async (session: string): Promise<boolean> => {
    const r = await redeem(session);
    if (r.status === "ready") { await install(r.md); return true; }
    if (r.status === "notfound") {
      stopPoll();
      setBuyMsg("That code wasn't recognised. If you just paid, give it a minute, then paste the code from your email below.");
      return false;
    }
    return false;   // pending
  };

  // Poll every 3s for ~3 minutes. Stops on install or timeout.
  const startPoll = (session: string) => {
    stopPoll();
    setPolling(true);
    setBuyMsg("Waiting for your payment to confirm — this unlocks automatically.");
    const started = Date.now();
    pollTimer.current = setInterval(async () => {
      if (Date.now() - started > 3 * 60 * 1000) {
        stopPoll();
        setBuyMsg("Your purchase is safe — paste the code from your email below to unlock it.");
        return;
      }
      try { await tryRedeem(session); } catch { /* keep polling */ }
    }, 3000);
  };

  // "Get — ₹3,000" → checkout for THIS skill (carrying the email) → open browser → start poll.
  const get = async (def: Premium) => {
    if (!emailOk) { setBuyMsg("Enter your email so we can send your receipt and unlock code."); return; }
    setBuyMsg(null);
    setBuyBusy(true);
    try {
      const { url, session } = await startCheckout(email.trim(), def.id);
      setPending(session, url, def.id, def.name);
      setResume(null);
      await openExternal(url);
      startPoll(session);
    } catch (e) {
      setBuyMsg((e as Error).message || "Couldn't start checkout. Please try again.");
    } finally {
      setBuyBusy(false);
    }
  };

  // "I've paid — check now" → immediate redeem on the pending session.
  const checkNow = async () => {
    const session = getPending() || resume;
    if (!session) { setBuyMsg("Start the purchase first, or paste the code from your email."); return; }
    setBuyMsg("Checking…");
    try {
      const ok = await tryRedeem(session);
      if (!ok && !polling) setBuyMsg("Not confirmed yet — give it a minute. Your purchase is safe.");
    } catch { setBuyMsg("Couldn't check just now. Try again in a moment."); }
  };

  // Paste-code → redeem the pasted session directly.
  const redeemCode = async () => {
    const session = code.trim();
    if (!session) return;
    setBuyMsg("Checking your code…");
    try {
      const r = await redeem(session);
      if (r.status === "ready") { await install(r.md); setCode(""); }
      else if (r.status === "notfound") setBuyMsg("That code wasn't recognised. Copy it exactly from your email.");
      else setBuyMsg("Not confirmed yet — if you just paid, give it a minute and try again.");
    } catch { setBuyMsg("Couldn't redeem that code just now — check your connection and try again."); }
  };

  // Resume an interrupted purchase: reopen the saved payment page (if any), then poll.
  const continueResume = async () => {
    if (!resume) return;
    const url = getPendingUrl();
    if (url) { try { await openExternal(url); } catch { /* browser blocked — poll still runs */ } }
    startPoll(resume);
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

        {resume && (
          <div className="pr-resume" role="status">
            <span>Finish your {pendingSkill.name || pendingDef.name} purchase.</span>
            <button className="pr-get" onClick={continueResume} disabled={polling}>Continue</button>
            <button className="link" onClick={checkNow}>I've paid — check now</button>
          </div>
        )}

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

          {/* Premium teasers — one per NOT-owned paid pack (owned ones already show as "Use" rows). */}
          {unowned.map((def) => (
            <li key={def.id} className="skill-row premium-teaser">
              <div className="pr-main">
                <div className="pr-head"><span className="pr-name">{def.name}</span></div>
                <p className="pr-desc">{def.desc}</p>
              </div>
              <div className="pr-buy">
                <span className="pr-price premium">Premium</span>
                {buyingId !== def.id && (
                  <button className="pr-get"
                    onClick={() => { setBuyMsg(null); setCode(""); setBuyingId(def.id); }} disabled={polling}>
                    {`Get — ${def.price}`}
                  </button>
                )}
              </div>
              {buyingId === def.id && (
                <div className="pr-email">
                  <span className="pr-redeem-label">Where should we send your receipt &amp; unlock code?</span>
                  <div className="pr-redeem-row">
                    <input className="pr-redeem-input" type="email" value={email} autoFocus
                      placeholder="you@email.com"
                      onChange={(e) => setEmail(e.target.value)} aria-label="Email for receipt"
                      onKeyDown={(e) => { if (e.key === "Enter" && emailOk && !buyBusy) get(def); }} />
                    <button className="pr-get" onClick={() => get(def)} disabled={buyBusy || polling || !emailOk}>
                      {buyBusy ? "Opening…" : "Continue →"}
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}

          {/* One shared "already paid? redeem" box — a code resolves to its skill server-side. */}
          {unowned.length > 0 && (
            <li className="skill-row premium-teaser">
              <div className="pr-redeem">
                <span className="pr-redeem-label">Already paid? Redeem code</span>
                <div className="pr-redeem-row">
                  <input className="pr-redeem-input" type="text" value={code}
                    placeholder="Paste the code from your email"
                    onChange={(e) => setCode(e.target.value)} aria-label="Redeem code" />
                  <button className="pr-get" onClick={redeemCode} disabled={!code.trim()}>Redeem</button>
                </div>
                {polling && <button className="link" onClick={checkNow}>I've paid — check now</button>}
                {buyMsg && <p className="pr-buy-note">{buyMsg}</p>}
              </div>
            </li>
          )}
        </ul>

        {installed && <p className="pr-got-note" role="status">{installedName} added ✓</p>}

        <div className="skills-import">
          <button className="link" onClick={doImport}>+ Import a skill…</button>
          <span className="skills-import-hint">Add a skill you downloaded — it lives in your library and survives reinstalls.</span>
          {importErr && <p className="error-inline">{importErr}</p>}
        </div>
      </div>
    </div>
  );
}
