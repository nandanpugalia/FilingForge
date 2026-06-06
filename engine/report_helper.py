"""The report helper — a single, app-managed file written to the library root.

A FilingForge Skill produces an HTML research report. The *visual* layer of that report
(the locked "Direction-C" house style: dark masthead, ember divider, numbered key findings,
a visual moat grid, a cited know/don't-know table) lives HERE, in one file the engine writes
to the library root as ``_filingforge-report.md``. Every skill — free or premium — references
this file via the library path it is already handed, so:

  • the visual layer is FREE and app-managed (a premium skill carries only analytical logic);
  • improving the look is a one-file change that every skill picks up on next run;
  • an enterprise client can be shipped a custom-branded helper without touching any skill.

The leading underscore sorts the file to the top of the library and signals "not a company".
The engine rewrites it on every library build, so a stale or hand-edited copy is replaced.
"""
from __future__ import annotations
from pathlib import Path

HELPER_NAME = "_filingforge-report.md"

# ── The locked house stylesheet (Direction-C). One file, zero dependencies, system fonts
#    only, print-optimised. Skills paste this verbatim — consistency IS the format. ──
_TEMPLATE = r"""# FilingForge — Report Template (house style)

> **This file is written and owned by the FilingForge app. Do not edit it — your changes
> are overwritten on the next library build.** A FilingForge Skill reads this file to render
> its result as a single, self-contained HTML report in the locked FilingForge house style.
> The analysis is the Skill's job; the *look* is defined here so every report is instantly
> recognisable and trustworthy on sight. Use the `<style>` block **verbatim** and write your
> content into the structure below it. Don't redesign it — consistency is the format.

## How a Skill uses this file

1. Do the analysis the Skill asks for (read the filings, form a view, gather cited facts).
2. Build **one self-contained `.html` file** using the `<style>` block and structure below.
3. Save it to `<TICKER>/research_report/<skill-slug>.html` inside the library, beside the
   filings, and also save the plain-text source as `<TICKER>/research_report/<skill-slug>.md`.
4. Make every citation a real, clickable `<a class="cite" href="../<path-from-INDEX>">` that
   opens the actual source PDF. A reader who can click a number and land on the filing trusts
   the work. Keep links as plain same-tab `<a>` (no `target`); the script below opens a new
   tab when the browser allows and falls back to same-tab (Safari blocks new windows to
   local `file://`). In a chat tool with no file access: keep the chips, drop the `href`.

## Portability — non-negotiable

- **One file, zero dependencies.** Inline all CSS and JS. No CDNs, no web fonts, no external
  images — **system fonts only**. It must render identically offline and as a Claude/ChatGPT
  artifact.
- **Vanilla JS only, lightly used.** If a script fails, the content stays fully readable.
- A static PDF is never needed: the report is print-optimised, so anyone can do
  `Cmd/Ctrl + P -> Save as PDF` and get a clean document.

## The house stylesheet — paste verbatim

```html
<style>
:root{
  --paper:#faf6ec;--ink:#1a1714;--ox:#7a1a2e;--ox2:#9a3346;--ember:#ff6a3d;
  --ember-deep:#d94f25;--muted:#6b5d4f;--rule:#e3d9c6;--tint:#f6eed8;--faint:#faf3e3;
  --dark:#1a1410;--dark2:#221a14;--good:#4a8a3a;
  --serif:Georgia,"Times New Roman",serif;--mono:ui-monospace,"SF Mono",Consolas,monospace;
}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:#e8e0d4;color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.62;-webkit-font-smoothing:antialiased}
#bar{position:fixed;top:0;left:0;height:3px;width:0;background:var(--ember);z-index:60;transition:width .1s linear}
.page{max-width:820px;margin:28px auto;background:var(--paper);box-shadow:0 6px 40px rgba(0,0,0,.18);border-radius:5px;overflow:hidden}

/* ── Dark masthead ── */
.pg-header{background:var(--dark);padding:38px 48px 28px;color:var(--paper)}
.ff-wordmark{font-family:var(--serif);font-size:13px;letter-spacing:.04em;color:var(--ember);font-weight:700;margin-bottom:16px}
.pg-eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;color:rgba(250,246,236,.42);margin-bottom:12px}
.pg-h1{font-size:40px;font-weight:400;line-height:1.05;letter-spacing:-.015em;color:var(--paper);margin:0}
.pg-tick{font-family:var(--mono);font-size:.32em;font-weight:600;color:rgba(250,246,236,.5);border:1px solid rgba(250,246,236,.2);border-radius:4px;padding:3px 9px;vertical-align:middle;margin-left:12px;white-space:nowrap}
.pg-dek{color:rgba(250,246,236,.6);font-style:italic;font-size:18px;margin:10px 0 0;line-height:1.45}
.pg-meta{font-family:var(--mono);font-size:11px;color:rgba(250,246,236,.32);margin-top:18px;letter-spacing:.02em}
.ember-rule{height:3px;background:var(--ember)}

/* ── Key findings (the lead) ── */
.findings{padding:30px 48px 24px;border-bottom:1px solid var(--rule)}
.findings-lbl{font-family:var(--mono);font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;color:var(--ox);font-weight:700;margin-bottom:16px}
.finding{display:flex;gap:16px;margin-bottom:14px;align-items:flex-start}
.finding-num{font-family:var(--mono);font-size:11px;color:var(--ember);font-weight:700;flex-shrink:0;width:20px;padding-top:3px}
.finding-text{font-size:16.5px;line-height:1.55}

/* ── Sections ── */
.section{padding:26px 48px}
.sec-header{display:flex;align-items:baseline;gap:16px;margin-bottom:16px;padding-bottom:11px;border-bottom:1px solid var(--rule)}
.sec-num{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--ox);letter-spacing:.08em}
.sec-h2{font-size:24px;font-weight:600;letter-spacing:-.01em;margin:0}
.sec-body h3{font-size:12.5px;font-family:var(--mono);text-transform:uppercase;letter-spacing:.13em;color:var(--ox);margin:18px 0 6px}
.sec-body p{font-size:15.5px;line-height:1.66;margin:0 0 13px}
.sec-body ul{margin:0 0 13px;padding-left:22px}.sec-body li{margin:5px 0}

/* ── Citations ── */
a.cite{font-family:var(--mono);font-size:.7em;color:var(--muted);border:1px solid var(--rule);border-radius:3px;padding:1px 5px;white-space:nowrap;text-decoration:none;letter-spacing:.01em}
a.cite:hover{color:var(--ember);border-color:var(--ember)}

/* ── Tables ── */
table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:14.5px;border-top:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink)}
thead th{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--ox);text-align:left;padding:9px 11px;border-bottom:1px solid var(--ink)}
td{padding:9px 11px;vertical-align:top;border-top:1px solid var(--rule)}
tbody tr:nth-child(odd) td{background:var(--faint)}
.num-cell{font-family:var(--mono);font-size:13.5px;white-space:nowrap}

/* ── Visual moat grid (six cells, colour = verdict) ── */
.moat-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;margin:10px 0 6px}
.moat-cell{border:1px solid var(--rule);border-radius:6px;padding:11px 13px}
.moat-name{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:5px}
.moat-verdict{font-size:14px;font-weight:700;margin-bottom:4px}
.moat-note{font-size:11.5px;color:var(--muted);line-height:1.42}
.moat-cell.yes{border-color:rgba(74,138,58,.32);background:rgba(74,138,58,.05)}
.moat-cell.yes .moat-verdict{color:var(--good)}
.moat-cell.weak{border-color:rgba(255,106,61,.3);background:rgba(255,106,61,.04)}
.moat-cell.weak .moat-verdict{color:var(--ember)}
.moat-cell.no .moat-verdict{color:var(--muted)}

/* ── Know / Don't-know two-column table ── */
.kdk{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}
.kdk th{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;padding:9px 13px;text-align:left}
.kdk th.know{color:var(--good);border-bottom:2px solid var(--good)}
.kdk th.dk{color:var(--ox);border-bottom:2px solid var(--ox)}
.kdk td{padding:8px 13px;vertical-align:top;border-top:1px solid var(--rule);line-height:1.5}
.kdk tr:nth-child(odd) td{background:var(--faint)}

/* ── Bar chart row (segment / geography splits) ── */
.barrow{display:grid;grid-template-columns:130px 1fr 150px;align-items:center;gap:13px;margin:9px 0;font-size:14px}
.barrow .seg{font-weight:600}
.barrow .track{background:var(--faint);border-radius:3px;height:22px;overflow:hidden}
.barrow .fill{height:100%;background:linear-gradient(90deg,var(--ox),var(--ember));border-radius:3px}
.barrow .val{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right}

/* ── Footer ── */
.pg-footer{padding:20px 48px 26px;border-top:1px solid var(--rule);display:flex;justify-content:space-between;font-family:var(--mono);font-size:11.5px;color:var(--muted);flex-wrap:wrap;gap:10px}
.pg-footer a{color:var(--ox);text-decoration:none}

@media(max-width:680px){.page{margin:0;border-radius:0}.pg-header,.findings,.section,.pg-footer{padding-left:24px;padding-right:24px}.pg-h1{font-size:30px}.moat-grid{grid-template-columns:1fr}}
@media print{body{background:#fff}#bar{display:none}.page{box-shadow:none;margin:0;max-width:none}.pg-header{-webkit-print-color-adjust:exact;print-color-adjust:exact}body{font-size:11pt}}
</style>
```

## The structure (fill with your content)

```html
<div id="bar"></div>
<div class="page">

  <header class="pg-header">
    <div class="ff-wordmark">FilingForge.</div>
    <div class="pg-eyebrow">{{SKILL NAME, e.g. Business Model Brief}}</div>
    <h1 class="pg-h1">{{Company Name}}<span class="pg-tick">{{TICKER}} · BSE {{code}}</span></h1>
    <p class="pg-dek">{{one-line thesis — what this business really is}}</p>
    <div class="pg-meta">Prepared from official BSE filings · Sources: {{N}} cited of {{M}} in index · {{FY}}</div>
  </header>
  <div class="ember-rule"></div>

  <section class="findings">
    <div class="findings-lbl">Key Findings</div>
    <!-- 4–6 numbered, cited findings. Each says something with a view, not a summary. -->
    <div class="finding"><span class="finding-num">01</span><span class="finding-text">{{finding}} <a class="cite" href="../{{path}}">[{{Filing, date}}]</a></span></div>
    <!-- … -->
  </section>

  <!-- One <section> per part of the report. Use tables, the moat grid, bar rows and the
       know/don't-know table where they sharpen a point. -->
  <section class="section">
    <div class="sec-header"><span class="sec-num">0X</span><h2 class="sec-h2">{{Section title}}</h2></div>
    <div class="sec-body"> … </div>
  </section>

  <footer class="pg-footer">
    <span>{{one-line provenance, e.g. Prepared from official BSE filings for TICKER.}}</span>
    <span>Filings gathered with <a href="https://filingforge.pages.dev">FilingForge · filingforge.pages.dev</a></span>
  </footer>

</div>
```

**Component cheat-sheet** (use where they help — don't force them):
- **Moat grid:** `<div class="moat-grid"><div class="moat-cell yes|weak|no"><div class="moat-name">…</div><div class="moat-verdict">Present|Modest|Not evident</div><div class="moat-note">…</div></div>…</div>`
- **Know/don't-know:** `<table class="kdk"><thead><tr><th class="know">Know</th><th class="dk">Don't know</th></tr></thead><tbody>…</tbody></table>`
- **Bar split:** `<div class="barrow"><span class="seg">Steel</span><div class="track"><div class="fill" style="width:76%"></div></div><span class="val">76% · ₹5,731 cr</span></div>`

## The script — reading-progress bar + citation handler (paste verbatim, near `</body>`)

```html
<script>
(function(){
  try{
    var bar=document.getElementById('bar');
    if(bar){
      var upd=function(){var h=document.documentElement;var sc=h.scrollTop||document.body.scrollTop;
        var mx=(h.scrollHeight-h.clientHeight)||1;bar.style.width=(100*sc/mx)+'%';};
      document.addEventListener('scroll',upd,{passive:true});upd();
    }
    document.querySelectorAll('a.cite[href]').forEach(function(a){
      if(a.getAttribute('href').charAt(0)==='#')return;
      a.addEventListener('click',function(e){
        var w=null;try{w=window.open(a.href,'_blank','noopener');}catch(_){}
        if(w)e.preventDefault();   // new tab opened -> don't also navigate this tab
      });
    });
  }catch(_){/* never let the script break the content */}
})();
</script>
```

## The bar — what makes a report worth keeping

- **A view, not a summary.** Take positions. Say what the business really is and the one
  thing that matters most. Never "the company operates across several segments."
- **Specific and quantified.** Real figures, each cited to its filing + date (page/slide
  where possible). No adjective stands in for a number.
- **Honest about gaps.** If the filings don't answer something, say so — credibility comes
  from what you refuse to claim. The know/don't-know table is where this lives.
- **Reads beautifully.** Tight prose; a table, chart or the moat grid where it sharpens a
  point. A reader should finish informed and want to send it to a colleague.

**Keep the footer.** It is how the work — and FilingForge — spreads.
"""


def write_report_helper(root: Path) -> Path:
    """Write (or overwrite) the report helper at ``root/_filingforge-report.md`` and return
    its path. Idempotent: same template every time. The app owns this file, so any stale or
    hand-edited copy is replaced on each library build."""
    root = Path(root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / HELPER_NAME
    path.write_text(_TEMPLATE, encoding="utf-8")
    return path
