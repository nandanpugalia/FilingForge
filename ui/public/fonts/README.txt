FilingForge — self-hosted fonts (council finding R9)
=====================================================

These woff2 files are SELF-HOSTED so the packaged (Tauri) app works fully
offline. Do NOT replace the @font-face rules in src/theme.css with a runtime
Google-Fonts @import — a packaged app may have no network.

Provenance
----------
Fetched from the Google Fonts CSS2 endpoint on 2026-06-04:

  https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=IBM+Plex+Mono:wght@400;500;600&display=swap

Both fonts are licensed under the SIL Open Font License 1.1 (free to bundle
and redistribute):
  - Fraunces      — Undercase Type / Phaedra Charles
  - IBM Plex Mono — IBM / Bold Monday

Files (latin + latin-ext subsets, matching Google's own subsetting):
  fraunces-400-latin.woff2        fraunces-400-latin-ext.woff2
  fraunces-600-latin.woff2        fraunces-600-latin-ext.woff2
  ibm-plex-mono-400-latin.woff2   ibm-plex-mono-400-latin-ext.woff2
  ibm-plex-mono-500-latin.woff2   ibm-plex-mono-500-latin-ext.woff2
  ibm-plex-mono-600-latin.woff2   ibm-plex-mono-600-latin-ext.woff2

manifest.json records the exact unicode-range for each subset (mirrored in
the @font-face rules in src/theme.css).

To refresh
----------
Re-run the CSS2 fetch above with a modern browser User-Agent (so Google
serves woff2 rather than ttf), parse each @font-face block for the latin /
latin-ext subset URLs, and re-download. Box-drawing / symbol glyphs
(▮ ▯ ✓ ⚙ ↗ ▲ ⌂ ▸ ≈) are intentionally NOT in these subsets and fall back to
the system monospace — same as on Google Fonts.
