"""The report helper — a single, app-managed file written to the library root.

A FilingForge Skill produces an HTML research report. The *visual* layer of that report
(the locked "Direction-C" house style, v2: dark masthead, ember divider, sticky context bar,
reading-progress bar, numbered key findings, a visual moat grid, an inline SVG narrative
chart, a cited know/don't-know table, fact-vs-analysis styling) lives HERE, in one file the
engine writes to the library root as ``_filingforge-report.md``. Every skill — free or
premium — references this file via the library path it is already handed, so:

  • the visual layer is FREE and app-managed (a premium skill carries only analytical logic);
  • improving the look is a one-file change that every skill picks up on next run;
  • an enterprise client can be shipped a custom-branded helper without touching any skill.

The leading underscore sorts the file to the top of the library and signals "not a company".
The engine rewrites it on every library build, so a stale or hand-edited copy is replaced.
"""
from __future__ import annotations
from pathlib import Path

HELPER_NAME = "_filingforge-report.md"

# ── The locked house stylesheet (Direction-C v2). One file, zero dependencies, system fonts
#    only, print-optimised. Skills paste this verbatim — consistency IS the format. The raw
#    (r"") prefix keeps the inline CSS/JS backslash escapes (e.g. \27E1, \2197) literal; there
#    is NO runtime substitution — the {{…}} placeholders are guidance for the AI, not .format. ──
_TEMPLATE = r"""# FilingForge — Report Template (house style)

> **This file is written and owned by the FilingForge app. Do not edit it — your changes
> are overwritten on the next library build.** A FilingForge Skill reads this file to render
> its result as a single, self-contained HTML report in the locked FilingForge house style
> (Direction-C, v2). The analysis is the Skill's job; the *look* is defined here so every
> report is instantly recognisable and trustworthy on sight. Use the `<style>` block and the
> `<script>` block **verbatim** and write your content into the structure between them. Don't
> redesign it — consistency is the format.

## How a Skill uses this file

1. Do the analysis the Skill asks for (read the filings, form a view, gather cited facts).
2. Build **one self-contained `.html` file** using the `<style>`, structure and `<script>`
   below.
3. Save it to `<TICKER>/research_report/<skill-slug>.html` inside the library, beside the
   filings, and also save the plain-text source as `<TICKER>/research_report/<skill-slug>.md`.
4. Make every citation a real, clickable `<a class="cite" href="../<path-from-INDEX>">` that
   opens the actual source PDF. A reader who can click a number and land on the filing trusts
   the work. Keep links as plain same-tab `<a>` (no `target`); the script below tries a new
   tab and falls back to same-tab (Safari blocks new windows to local `file://`). Add an
   optional `data-q="<exact quote from the filing>"` so the chip shows the source line on
   hover. In a chat tool with no file access: keep the chips, drop the `href`.

## Fact vs analysis — keep them visibly separate

A cited fact and your own reasoning must never blur. Cited facts sit in normal `<p>` prose
with a `<a class="cite">` chip. **Your own inference** goes in a `<span class="infer">…</span>`
block — it renders italic, indented, and auto-labelled "Analysis", so a reader always knows
where the filings end and the tool's judgement begins.

## The narrative chart — and when to OMIT it

Section "Revenue streams & trajectory" can carry an inline SVG chart (`<svg id="trend">`)
that draws revenue bars + an EBITDA-margin line straight from `data-rev` / `data-margin` /
`data-years` attributes — no libraries, drawn by the script below. It is the single most
persuasive element in the report **when the data is clean**.

> **If the filings don't yield clean multi-year revenue + margin data, OMIT the chart
> entirely — never render an empty `<figure class='chart'>`.** A missing chart is invisible;
> an empty or fabricated one destroys trust. Omit the chart if the data isn't available, and
> let the prose and tables carry the section instead.

## Portability — non-negotiable

- **One file, zero dependencies.** Inline all CSS and JS. No CDNs, no web fonts, no external
  images — **system fonts only**. It must render identically offline and as a Claude/ChatGPT
  artifact.
- **Vanilla JS only, lightly used.** If a script fails, the content stays fully readable
  (the chart, progress bar, sticky context bar and collapse are all enhancements).
- A static PDF is never needed: the report is print-optimised, so anyone can do
  `Cmd/Ctrl + P -> Save as PDF` and get a clean document.

## The house stylesheet — paste verbatim (inside `<head>`)

```html
<style>
:root{
  --paper:#faf6ec;--ink:#1a1714;--ox:#7a1a2e;--ox2:#9a3346;--ember:#ff6a3d;
  --ember-deep:#d94f25;--muted:#7a6b5c;--rule:#e3d9c6;--tint:#f6eed8;--faint:#faf3e3;
  --dark:#15110d;--dark2:#1f1812;--good:#4a8a3a;--line:#2f6b8f;
  --serif:Georgia,"Times New Roman",serif;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:#0d0b09;color:var(--ink);font-family:var(--serif);font-size:17px;line-height:1.6;letter-spacing:.006em;-webkit-font-smoothing:antialiased}
#bar{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,var(--ox),var(--ember));z-index:90;transition:width .08s linear}

/* sticky context bar — institutional orientation, not decorative dots */
#ctx{position:fixed;top:0;left:0;right:0;height:38px;background:rgba(21,17,13,.96);color:var(--paper);z-index:80;display:flex;align-items:center;gap:14px;padding:0 22px;font-family:var(--mono);font-size:11.5px;letter-spacing:.02em;border-bottom:1px solid var(--ember);transform:translateY(-100%);transition:transform .28s}
#ctx.show{transform:none}
#ctx .co{font-weight:700;color:var(--paper)}
#ctx .sec{color:rgba(250,246,236,.55);flex:1}
#ctx .cites{color:var(--ember)}

.page{max-width:880px;margin:0 auto;background:var(--paper);min-height:100vh;box-shadow:0 0 80px rgba(0,0,0,.5)}

/* ── Masthead (dark) ── */
.pg-header{background:var(--dark);color:var(--paper);padding:54px 56px 30px;position:relative}
.ff-wordmark{font-family:var(--serif);font-size:14px;letter-spacing:.04em;color:var(--ember);font-weight:700;margin-bottom:22px}
.pg-eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.26em;text-transform:uppercase;color:rgba(250,246,236,.4);margin-bottom:13px}
.pg-h1{font-size:clamp(32px,4.6vw,48px);font-weight:400;line-height:1.04;letter-spacing:-.02em;margin:0}
.pg-tick{display:inline-block;font-family:var(--mono);font-size:.3em;font-weight:600;color:rgba(250,246,236,.5);border:1px solid rgba(250,246,236,.22);border-radius:5px;padding:4px 11px;vertical-align:middle;margin-left:13px}
/* provenance line */
.prov{font-family:var(--mono);font-size:11px;color:rgba(250,246,236,.5);margin-top:16px;line-height:1.7;letter-spacing:.02em}
.prov b{color:rgba(250,246,236,.75);font-weight:600}
/* condensed stat strip (static, tabular) */
.stats{display:flex;flex-wrap:wrap;gap:0;margin-top:26px;border-top:1px solid rgba(250,246,236,.12);border-bottom:1px solid rgba(250,246,236,.12)}
.stat{padding:16px 22px 16px 0;margin-right:22px;border-right:1px solid rgba(250,246,236,.12)}
.stat:last-child{border-right:0}
.stat .v{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--paper);line-height:1;font-variant-numeric:tabular-nums}
.stat .v .u{font-size:12px;color:rgba(250,246,236,.5);margin-left:2px}
.stat .l{font-family:var(--mono);font-size:9.5px;color:rgba(250,246,236,.45);letter-spacing:.12em;text-transform:uppercase;margin-top:8px}
.ember-rule{height:3px;background:linear-gradient(90deg,var(--ox),var(--ember))}

/* ── Thesis (lead with conviction) ── */
.thesis{margin:0;padding:26px 56px;background:rgba(255,106,61,.05);border-bottom:1px solid var(--rule)}
.thesis .tl{font-family:var(--mono);font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--ox);font-weight:700;margin-bottom:10px}
.thesis p{font-size:21px;line-height:1.5;margin:0;border-left:4px solid var(--ember);padding-left:20px;font-style:italic;color:#2a211a;max-width:64ch}

/* ── Key findings (the lead) ── */
.findings{padding:30px 56px 24px;border-bottom:1px solid var(--rule)}
.findings-lbl{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--ox);font-weight:700;margin-bottom:16px}
.finding{display:flex;gap:15px;margin-bottom:13px;align-items:baseline}
.finding-num{font-family:var(--mono);font-size:11px;color:var(--ox);font-weight:700;flex:0 0 auto;width:22px}
.finding-text{font-size:16px;line-height:1.5;max-width:66ch}

/* ── Sections (collapse via chevron only) ── */
.section{padding:28px 56px;border-top:1px solid var(--rule)}
.sec-header{display:flex;align-items:center;gap:15px;padding:2px 0}
.sec-num{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--ox);letter-spacing:.08em}
.sec-h2{font-size:24px;font-weight:600;letter-spacing:-.01em;margin:0;flex:1}
.sec-chev{color:var(--muted);font-family:var(--mono);font-size:12px;transition:transform .3s;cursor:pointer;padding:6px}
.section.collapsed .sec-chev{transform:rotate(-90deg)}
.sec-body{max-height:6000px;overflow:hidden;transition:max-height .4s ease,opacity .3s,margin .3s;opacity:1;margin-top:13px}
.section.collapsed .sec-body{max-height:0;opacity:0;margin-top:0}
.sec-body h3{font-size:12.5px;font-family:var(--mono);text-transform:uppercase;letter-spacing:.13em;color:var(--ox);margin:18px 0 6px;border-left:3px solid var(--ember);padding-left:11px}
.sec-body p{font-size:15.5px;line-height:1.62;margin:0 0 13px;max-width:66ch}
.sec-body ul{margin:0 0 13px;padding-left:22px}.sec-body li{margin:5px 0}
/* fact vs inference: the tool's own reasoning is marked + italic */
.infer{display:block;font-style:italic;color:#3a2f26;border-left:2px solid var(--rule);padding-left:14px;margin:0 0 13px;max-width:64ch}
.infer::before{content:"\27E1  Analysis  ";font-style:normal;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

/* citations — visible, verifiable, hover to see source quote */
a.cite{font-family:var(--mono);font-size:.7em;color:var(--ox);background:var(--tint);border:1px solid rgba(122,26,46,.22);border-radius:3px;padding:1px 6px 1px 5px;white-space:nowrap;text-decoration:none;font-weight:600;position:relative;transition:.15s}
a.cite::after{content:"\2197";font-size:.85em;margin-left:2px;opacity:.6}
a.cite:hover{color:#fff;background:var(--ox);border-color:var(--ox)}
a.cite[data-q]:hover::before{content:attr(data-q);position:absolute;left:0;bottom:140%;width:280px;background:var(--dark);color:var(--paper);font-family:var(--serif);font-style:italic;font-size:13px;font-weight:400;line-height:1.45;letter-spacing:0;padding:11px 13px;border-radius:6px;border-left:3px solid var(--ember);box-shadow:0 8px 28px rgba(0,0,0,.3);white-space:normal;z-index:30;text-transform:none}

/* ── Tables ── */
table{border-collapse:collapse;width:100%;margin:10px 0 18px;font-size:14.5px;border-top:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink)}
thead th{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--ox);text-align:left;padding:9px 11px;border-bottom:1px solid var(--ink)}
td{padding:9px 11px;vertical-align:top;border-top:1px solid var(--rule)}
tbody tr:nth-child(odd) td{background:var(--faint)}
.num-cell{font-family:var(--mono);font-size:13.5px;white-space:nowrap;font-variant-numeric:tabular-nums}

/* ── The narrative chart (the wow) ── */
figure.chart{margin:14px 0 18px;padding:18px 20px 12px;border:1px solid var(--rule);border-radius:10px;background:#fff}
figure.chart svg{width:100%;height:auto;display:block}
figure.chart .legend{display:flex;gap:18px;font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:10px;flex-wrap:wrap}
figure.chart .legend i{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:6px;border-radius:2px}
figcaption{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:8px;line-height:1.5}

/* ── Visual moat grid (six cells, colour = verdict, evidence VISIBLE + confidence tag) ── */
.moat-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:11px;margin:12px 0 6px}
.moat-cell{border:1px solid var(--rule);border-radius:9px;padding:13px 15px;background:#fff}
.moat-name{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:7px}
.moat-verdict{font-size:15px;font-weight:700;display:flex;align-items:center;gap:7px}
.moat-verdict::before{content:"";width:9px;height:9px;border-radius:50%;flex:0 0 auto}
.moat-conf{font-family:var(--mono);font-size:9px;color:var(--muted);font-weight:400;margin-left:auto;letter-spacing:.04em}
.moat-note{font-size:12px;color:var(--muted);line-height:1.45;margin-top:8px}
.moat-cell.yes{border-color:rgba(74,138,58,.35);background:rgba(74,138,58,.04)}.moat-cell.yes .moat-verdict{color:var(--good)}.moat-cell.yes .moat-verdict::before{background:var(--good)}
.moat-cell.weak{border-color:rgba(255,106,61,.32);background:rgba(255,106,61,.035)}.moat-cell.weak .moat-verdict{color:var(--ember-deep)}.moat-cell.weak .moat-verdict::before{background:var(--ember)}
.moat-cell.no .moat-verdict{color:var(--muted)}.moat-cell.no .moat-verdict::before{background:var(--muted)}

/* ── Know / Don't-know two-column table ── */
.kdk{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}
.kdk th{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;padding:9px 13px;text-align:left}
.kdk th.know{color:var(--good);border-bottom:2px solid var(--good)}
.kdk th.dk{color:var(--ox);border-bottom:2px solid var(--ox)}
.kdk td{padding:8px 13px;vertical-align:top;border-top:1px solid var(--rule);line-height:1.5;width:50%}
.kdk tr:nth-child(odd) td{background:var(--faint)}

.disclaimer{padding:18px 56px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--muted);font-style:italic;line-height:1.55;max-width:72ch}

/* ── Footer ── */
.pg-footer{padding:22px 56px 40px;border-top:1px solid var(--rule);display:flex;justify-content:space-between;font-family:var(--mono);font-size:11.5px;color:var(--muted);flex-wrap:wrap;gap:10px}
.pg-footer a{color:var(--ox);text-decoration:none}

@media(max-width:720px){.pg-header,.thesis,.findings,.section,.disclaimer,.pg-footer{padding-left:22px;padding-right:22px}.moat-grid{grid-template-columns:1fr}#ctx .sec{display:none}.pg-h1{font-size:30px}}
@media print{
  body{background:#fff}#bar,#ctx{display:none}.page{box-shadow:none;max-width:none;margin:0}
  .section.collapsed .sec-body{max-height:none!important;opacity:1!important}
  .pg-header,.thesis,.moat-cell{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  body{font-size:11pt}
}
</style>
```

## The structure (fill with your content)

> Wrap everything in a full HTML document — `<!DOCTYPE html><html><head><meta charset="utf-8">…<style>…(the locked CSS)…</style></head><body>…(the structure below)…<script>…(the locked JS)…</script></body></html>`. The fragment below is the `<body>` content only; never ship a bare fragment.

```html
<div id="bar"></div>
<div id="ctx"><span class="co">{{Company Name}}</span><span class="sec" id="ctxSec">{{SKILL NAME}}</span><span class="cites">{{N}} sources cited</span></div>

<div class="page">

  <header class="pg-header">
    <div class="ff-wordmark">FilingForge.</div>
    <div class="pg-eyebrow">{{SKILL NAME, e.g. Business Model Brief}}</div>
    <h1 class="pg-h1">{{Company Name}}<span class="pg-tick">{{TICKER}} · BSE {{code}}</span></h1>
    <div class="prov">
      <b>Sources:</b> {{filing · date · …}} &nbsp;·&nbsp; <b>Generated:</b> {{date}} · FilingForge {{version}}<br>
      <b>Covers:</b> {{what this report answers}} &nbsp;·&nbsp; <b>Excludes:</b> {{what the filings don't disclose}}
    </div>
    <!-- 3–4 headline numbers, each cited elsewhere in the body. Omit the strip if there
         aren't clean numbers to show. -->
    <div class="stats">
      <div class="stat"><div class="v">{{value}}<span class="u">{{unit}}</span></div><div class="l">{{label}}</div></div>
    </div>
  </header>
  <div class="ember-rule"></div>

  <div class="thesis">
    <div class="tl">The thesis in one line</div>
    <p>{{one sentence — what this business really is and the single variable that matters}}</p>
  </div>

  <section class="findings">
    <div class="findings-lbl">Key Findings</div>
    <!-- 4–6 numbered, cited findings. Each says something with a view, not a summary. -->
    <div class="finding"><span class="finding-num">01</span><span class="finding-text">{{finding}} <a class="cite" href="../{{path}}" data-q="{{exact source quote}}">[{{Filing, date}}]</a></span></div>
    <!-- … -->
  </section>

  <!-- One <section data-nav="short label"> per part of the report. Use tables, the chart,
       the moat grid and the know/don't-know table where they sharpen a point. -->
  <section class="section" data-nav="{{short label}}">
    <div class="sec-header"><span class="sec-num">0X</span><h2 class="sec-h2">{{Section title}}</h2><span class="sec-chev">▼</span></div>
    <div class="sec-body">
      <p>{{cited fact prose}} <a class="cite" href="../{{path}}" data-q="{{quote}}">[{{cite}}]</a></p>
      <span class="infer">{{your own reasoning — auto-labelled "Analysis"}}</span>
    </div>
  </section>

  <div class="disclaimer">Generated by FilingForge from official BSE filings. Figures should be verified against the original filings linked in each citation. This is research tooling, not investment advice.</div>

  <footer class="pg-footer">
    <span>{{one-line provenance, e.g. Prepared from official BSE filings for TICKER.}}</span>
    <span>Filings gathered with <a href="https://filingforge.pages.dev">FilingForge · filingforge.pages.dev</a></span>
  </footer>

</div>
```

**Component cheat-sheet** (use where they help — don't force them):
- **Narrative chart** (omit if you don't have clean multi-year data — see above):
  ```html
  <figure class="chart">
    <svg id="trend" viewBox="0 0 720 300" role="img" aria-label="Revenue and EBITDA margin"
         data-years="FY22,FY23,FY24,FY25,FY26"
         data-rev="6200,6850,7100,7436,7540"
         data-margin="9.8,8.6,9.1,8.9,7.9"
         data-notes="2:new line commissioned,4:spread compression"></svg>
    <div class="legend"><span><i style="background:linear-gradient(90deg,#7a1a2e,#ff6a3d)"></i>Revenue (₹ cr)</span><span><i style="background:#2f6b8f"></i>EBITDA margin (%)</span></div>
    <figcaption>{{what the picture says}}. Source: {{cite}}.</figcaption>
  </figure>
  ```
- **Moat grid:** `<div class="moat-grid"><div class="moat-cell yes|weak|no"><div class="moat-name">…</div><div class="moat-verdict">Present|Modest|Not evident <span class="moat-conf">N cites</span></div><div class="moat-note">…</div></div>…</div>`
- **Know/don't-know:** `<table class="kdk"><thead><tr><th class="know">Know</th><th class="dk">Don't know</th></tr></thead><tbody>…</tbody></table>`

## The script — progress bar + sticky context + collapse + chart + Safari-safe citations

Paste this verbatim near `</body>`. It draws the chart from the `data-*` attributes (so there
is nothing to draw — and nothing breaks — if you omit the `<svg id="trend">`), drives the
reading-progress bar and sticky context bar, and handles citation clicks Safari-safely.

```html
<script>
(function(){
 try{
  var bar=document.getElementById('bar');
  if(bar){var upd=function(){var h=document.documentElement,sc=h.scrollTop||document.body.scrollTop,mx=(h.scrollHeight-h.clientHeight)||1;bar.style.width=(100*sc/mx)+'%';};
    addEventListener('scroll',upd,{passive:true});upd();}

  // sticky context bar appears past hero; shows current section
  var ctx=document.getElementById('ctx'),ctxSec=document.getElementById('ctxSec');
  if(ctx){addEventListener('scroll',function(){ctx.classList.toggle('show',scrollY>360);},{passive:true});
    if(ctxSec){var secs=[].slice.call(document.querySelectorAll('.section[data-nav]'));
      if(window.IntersectionObserver&&secs.length){var spy=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)ctxSec.textContent=e.target.getAttribute('data-nav');});},{rootMargin:'-40% 0px -55% 0px'});
        secs.forEach(function(s){spy.observe(s);});}}}

  // collapse via chevron ONLY (never lose your place clicking a heading)
  document.querySelectorAll('.sec-chev').forEach(function(c){c.addEventListener('click',function(e){e.stopPropagation();c.closest('.section').classList.toggle('collapsed');});});

  // citations: try a new tab; if the browser blocks it (Safari refuses a new window to a
  // local file://), fall back to same-tab so the PDF ALWAYS opens. Always preventDefault
  // first, then decide — never leave a dead truthy window swallow the click.
  document.querySelectorAll('a.cite[href]').forEach(function(a){
    var href=a.getAttribute('href'); if(!href||href.charAt(0)==='#')return;
    a.addEventListener('click',function(e){
      e.preventDefault();
      var w=null; try{w=window.open(href,'_blank','noopener');}catch(_){}
      if(!w){ window.location.href=href; }   // blocked → same tab, guaranteed to open
    });
  });

  // ── narrative chart: revenue bars + margin line, drawn from data-* (no libs) ──
  var svg=document.getElementById('trend');
  // Draw only when all three data series are present — a bare/malformed SVG stub
  // (e.g. the AI kept the element but forgot the data-* attrs) cleanly no-ops.
  if(svg&&(!svg.dataset.years||!svg.dataset.rev||!svg.dataset.margin))svg=null;
  if(svg){
    var NS='http://www.w3.org/2000/svg',W=720,H=300,padL=54,padR=48,padT=24,padB=46;
    var yrs=svg.dataset.years.split(','),rev=svg.dataset.rev.split(',').map(Number),mar=svg.dataset.margin.split(',').map(Number);
    var notes={};(svg.dataset.notes||'').split(',').forEach(function(nn){var p=nn.split(':');if(p.length===2)notes[+p[0]]=p[1];});
    var n=yrs.length,plotW=W-padL-padR,plotH=H-padT-padB;
    var revMax=Math.max.apply(null,rev)*1.12,marMin=Math.min.apply(null,mar)-1,marMax=Math.max.apply(null,mar)+1;
    var bx=function(i){return padL+plotW*(i+0.5)/n;};
    var revY=function(v){return padT+plotH*(1-v/revMax);};
    var marY=function(v){return padT+plotH*(1-(v-marMin)/(marMax-marMin));};
    function el(t,a){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);return e;}
    for(var g=0;g<=3;g++){var gv=revMax*g/3,gy=revY(gv);svg.appendChild(el('line',{x1:padL,y1:gy,x2:W-padR,y2:gy,stroke:'#e3d9c6','stroke-width':1}));var tl=el('text',{x:padL-8,y:gy+3,'text-anchor':'end','font-family':'ui-monospace,monospace','font-size':9,fill:'#9a8c7c'});tl.textContent=Math.round(gv);svg.appendChild(tl);}
    var defs=el('defs',{}),lg=el('linearGradient',{id:'gb',x1:0,y1:1,x2:0,y2:0});lg.appendChild(el('stop',{offset:'0%','stop-color':'#7a1a2e'}));lg.appendChild(el('stop',{offset:'100%','stop-color':'#ff6a3d'}));defs.appendChild(lg);svg.appendChild(defs);
    var bw=plotW/n*0.46;
    rev.forEach(function(v,i){var y=revY(v),x=bx(i)-bw/2;svg.appendChild(el('rect',{x:x,y:y,width:bw,height:padT+plotH-y,fill:'url(#gb)',rx:2}));
      var yr=el('text',{x:bx(i),y:H-padB+16,'text-anchor':'middle','font-family':'ui-monospace,monospace','font-size':10,fill:'#7a6b5c'});yr.textContent=yrs[i];svg.appendChild(yr);});
    var pts=mar.map(function(v,i){return bx(i)+','+marY(v);}).join(' ');
    svg.appendChild(el('polyline',{points:pts,fill:'none',stroke:'#2f6b8f','stroke-width':2.5,'stroke-linejoin':'round'}));
    mar.forEach(function(v,i){svg.appendChild(el('circle',{cx:bx(i),cy:marY(v),r:3.5,fill:'#fff',stroke:'#2f6b8f','stroke-width':2}));
      var ml=el('text',{x:bx(i),y:marY(v)-9,'text-anchor':'middle','font-family':'ui-monospace,monospace','font-size':9,fill:'#2f6b8f','font-weight':'700'});ml.textContent=v+'%';svg.appendChild(ml);});
    for(var k in notes){var ii=+k;if(ii<0||ii>=n)continue;var ax=bx(ii),ay=marY(mar[ii]);svg.appendChild(el('line',{x1:ax,y1:ay+6,x2:ax,y2:ay+24,stroke:'#9a8c7c','stroke-width':1,'stroke-dasharray':'2 2'}));var an=el('text',{x:Math.min(ax,W-padR-150),y:ay+36,'font-family':'ui-monospace,monospace','font-size':9,fill:'#7a6b5c'});an.textContent=notes[k];svg.appendChild(an);}
  }
 }catch(_){/* never let the script break the content */}
})();
</script>
```

## The bar — what makes a report worth keeping

- **A view, not a summary.** Take positions. Say what the business really is and the one
  thing that matters most. Never "the company operates across several segments."
- **Specific and quantified.** Real figures, each cited to its filing + date (page/slide
  where possible). No adjective stands in for a number.
- **Fact and analysis kept apart.** Cited facts in prose; your reasoning in `.infer`.
- **Honest about gaps.** If the filings don't answer something, say so — credibility comes
  from what you refuse to claim. The know/don't-know table is where this lives, and the chart
  is omitted rather than faked when the data isn't there.
- **Reads beautifully.** Tight prose; a table, the chart or the moat grid where it sharpens a
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
