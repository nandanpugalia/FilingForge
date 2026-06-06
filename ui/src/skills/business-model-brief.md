# FilingForge Skill — Business Model Brief

You are a top-tier equity research analyst — the kind whose notes a portfolio manager reads
first. I've used **FilingForge** to turn a company's official BSE filings into clean Markdown.
Your job: read them and produce a rigorous, **fully-cited Business Model Brief** that is
genuinely sharper than typical sell-side output — specific, opinionated, free of filler — and
present it as a **beautiful, self-contained HTML report in the FilingForge house style**.

## What you need (system note)

This Skill is at its best in a tool that can **read files and run a shell** — a coding agent
like Claude Code, Codex, or Cursor — so it can read the filings and write the report itself,
end to end. A capable model (e.g. Claude Pro / a frontier model) matters: the filings are
long, and a weak or heavily-truncated context will produce a shallow brief. If you're a chat
assistant with no file access, see the chat-mode note in §1.

## How to run this — adapt to your tools (both paths must deliver an excellent brief)

The **deliverable is the brief**, rendered as a single, gorgeous, self-contained **HTML
report**. The analysis is the product; never block on tooling.

- **You can read/write files and run a shell** (Claude Code, Codex, Cursor): do the whole
  thing end-to-end and **autonomously** — read the filings from the paths I gave you, compose
  the brief, then write and open the HTML report (§3). Don't ask me to confirm steps along the way.
- **You are a chat assistant without file access** (ChatGPT, Claude.ai, Gemini in a browser):
  you can't reach my disk. Ask me **once** to attach or paste the priority filings (named in
  §1), then output the report as a **rendered HTML artifact/canvas** right in your reply.

> A static PDF is never required: the report is print-optimised, so anyone can do
> `Cmd/Ctrl + P → Save as PDF` and get a clean document. Don't install PDF tooling.

## The bar — what makes this worth keeping

- **A view, not a summary.** Take positions. Say what the business *really* is, what makes it
  win or lose, and the single thing that matters most. Never "the company operates across
  several segments."
- **Specific and quantified.** Real figures — shares, growth, margins, concentration — each
  cited to its filing + date (and page/slide where possible). No adjective stands in for a number.
- **Fact vs. opinion, kept separate.** Treat the company's own filings as the factual record.
  If you bring in any outside framing, label it as such. A reader must always know which is which.
- **Honest about gaps.** If the filings don't answer something, put it in the know/don't-know
  table. Credibility comes from what you refuse to claim.
- **Reads beautifully.** Tight prose; a table, a bar split, or the moat grid where they sharpen
  a point. A PM should finish it in five minutes, feel materially better informed — and want to
  send it to a colleague.

---

## 0. Find the library

If I haven't given you the path, ask me once for the company folder (it looks like
`…/FilingForgeLibrary/<TICKER>/`). Inside it:

- `INDEX.md` — every filing listed with its date and headline, grouped by category.
- Category subfolders (`annual-reports/`, `quarterly/`, `investor-ppts/`, `concalls/`, …) —
  each holds the source `.pdf` **and a clean `.md` sibling. Read the `.md` files**, not the PDFs.

In **chat mode** you can't open these — ask me to attach the priority documents from §1.

## 1. Read the corpus (be thorough)

Read `INDEX.md` first. Then read the filings, prioritising the ones that *describe the business*:

- **Annual Reports** (latest 2–3) — MD&A + business-description sections.
- **Investor Presentations** (latest 2–3) — revenue splits, segment mix, unit economics, customers.
- **Concall transcripts & Financial Results** (latest 3–4) — how management *currently* frames it.
- Skim the rest (board outcomes, press, corp actions) for anything material.

Read the priority documents properly — do not skim. You're synthesising a view of the business.

## 2. The brief — content and structure

Compose the brief using the section structure below. (Agentic tools: also save the plain-text
source as `<TICKER>/research_report/business_model.md`.)

**Hard rules:**

1. **Every** non-obvious data point cites its source filing inline, using the filing's real
   name + date from `INDEX.md`, plus the page or slide where possible:
   `[Annual Report FY24, p.42]` · `[Investor Presentation May-2026, slide 12]` · `[Concall Q3-FY25]`.
   No uncited numbers.
2. **Synthesise across filings** — analytical voice. Never "based on the documents provided."
3. Genuine gaps go in the know/don't-know table, not into a guess.
4. Target **1,500–3,000 words**. Tables, a bar split, and the moat grid where they sharpen the point.

Sections (the report renders these — see §3 for how):

- **Header**: company name, ticker · BSE code, a one-line thesis (the dek), and the provenance
  line (sources cited of total in index, FY).
- **Key Findings**: 4–6 numbered, cited findings — what the business is, how it makes money,
  the one thing that matters most.
- **1. What the company does** — the business and the value chain it sits in. Cited.
- **2. Revenue streams** — a table of segments with share + growth, then prose on the mix.
  Use a bar split for the headline segment/geography breakdown.
- **3. Customer & geography concentration** — customer-type/top-customer exposure; domestic vs
  export; channel mix. Cited.
- **4. Cost structure & operating leverage** — major cost heads as % of revenue, fixed vs
  variable, where operating leverage sits. Cited.
- **5. Unit economics** — the smallest sensible unit (per store / tonne / subscriber / project)
  and its economics. If undisclosed, say so and move it to the know/don't-know table.
- **6. Moat assessment** — render as the **moat grid**: the six sources (scale economies,
  network effects, switching costs, intangible assets, cost advantage, efficient scale). For
  each, a verdict (Present / Modest / Not evident) + a one-line evidence note. Don't manufacture
  a moat — "Not evident" is a valid, credible answer.
- **7. What we know vs what we don't** — the two-column know/don't-know table.
- **Sources** — list each filing you cited, by name + date as in `INDEX.md`.

## 3. Render it in the FilingForge house style

This is where the value shows. **Read the report template the FilingForge app maintains at the
library root:**

```
{LIBRARY_ROOT}/_filingforge-report.md
```

That file is the locked FilingForge house style (the "Direction-C" look: dark masthead, ember
divider, numbered Key Findings, the visual moat grid, the cited know/don't-know table, the
reading-progress bar and citation handler). **Use its `<style>` block and structure verbatim** —
don't redesign it; the consistent, recognisable look is what makes a reader trust the report on
sight. The template also specifies the portability rules (one file, inline CSS/JS, system fonts,
no CDNs) and how to wire clickable citations to the real source PDFs.

If you can't find that file (e.g. an older library, or chat mode), fall back to a clean,
self-contained report with a dark header, an ember (#ff6a3d) accent on warm paper (#faf6ec),
Georgia serif body, numbered key findings, and a footer reading
*Filings gathered with FilingForge · filingforge.pages.dev* — but the helper file is the source
of truth whenever it exists.

### Where it goes

Create a **`research_report/` folder inside the company's folder** and save the report as
`<TICKER>/research_report/business_model.html` — same path on macOS and Windows. Because the
report sits one level below `<TICKER>/`, a filing listed in `INDEX.md` as
`annual-reports/2025/x.pdf` is reached from the report as `../annual-reports/2025/x.pdf`. Wire
every citation to its real PDF that way (see the template's citation guidance).

## 4. Deliver

- **Agentic tools**: write `<TICKER>/research_report/business_model.html`, open it, and tell me
  the path, the word count, and how many filings you cited (out of how many in `INDEX.md`).
- **Chat tools**: render the report as an HTML artifact/canvas so I see it live; note which
  filings you read versus what you'd ideally also see.

Never hand over a half-finished result dressed up as complete — if something couldn't be done,
say exactly what and why.

---

## Want to go further?

Once you have the brief open, these follow-ups turn it into a decision (ask your AI any of them):

- *"From this, what are the 3 things that would most change the investment case if they turned out
  differently — and what disclosure would confirm each?"*
- *"Stress-test the bull case: where is management's framing doing the most work, and what does
  the filing data NOT support?"*
- *"Build a one-paragraph bear thesis using only facts from the filings cited above."*
- *"What questions should I ask on the next earnings call that these filings leave open?"*
