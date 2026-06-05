# Changelog

All notable changes to FilingForge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- _macOS build pending Apple notarization — landing shortly._

## [0.1.2] — 2026-06-05

### Fixed
- In-app **Report a bug / request a feature** now opens a prefilled GitHub issue in
  your browser (previously a placeholder that accepted input but didn't deliver it).

## [0.1.1] — 2026-06-05

### Added
- Search any **BSE-listed** Indian company and download its official filings
  (annual reports, results, investor presentations, and more).
- Convert each filing PDF to a clean Markdown sibling — text-based extraction,
  no OCR; scanned-image PDFs are saved as-is and clearly flagged.
- Per-company and master **`INDEX.md`** so your AI can navigate the library.
- **Year-wise** library layout with smart, incremental refresh (pulls only what's new).
- **Skills** — prompt-packs you run in your own Claude or Codex. First Skill:
  **Business Model Brief** (free).
- One-window desktop app for **Windows** (macOS build in final notarization, landing
  shortly), with **signed auto-updates** (Tauri update-signing key).
- Local-first throughout: no account, no telemetry, the app never calls an LLM.
