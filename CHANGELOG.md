# Changelog

All notable changes to FilingForge are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.8] — 2026-06-07

### Added
- **Pre-release updates channel.** A new Settings toggle, *"Get pre-release updates"* (off by
  default), lets you opt in to try new versions early — before they roll out to everyone. This
  lets the project test each release on real installs first, so stable updates are safer.

### Changed
- The in-app updater now selects its feed (stable or pre-release) based on your preference, with
  the update check folded into the existing once-a-day check (no extra background activity).

## [0.1.7] — 2026-06-06

### Added
- **See what you'll download before it starts.** Picking a company now shows a preview —
  how many filings will be fetched, broken down by type, and how many you already have — so
  you approve before anything downloads. No more a five-year pull starting blind.
- **A Stop button** during a download. It finishes the file in flight, keeps everything
  already saved (fully indexed), and never leaves your library half-written.
- **Smarter defaults.** New libraries pull the high-signal filings by default (annual reports,
  results, investor presentations, concall transcripts — now tagged *Recommended*) over
  **2 years** of history, instead of every routine notice and postal ballot. Tick **All
  filings** to pull everything. The app **remembers the scope you last chose** as your next
  default, and refreshing an existing library keeps whatever categories you originally chose.

### Fixed
- **Your library can no longer be corrupted by an interrupted download.** Every file is now
  written atomically — a Stop, a window-close, a crash or a dropped connection can never leave
  a half-written PDF or Markdown that the index would treat as real. (This also hardens older
  libraries against the same problem going forward.)
- Network reads time out faster (30s), so **Stop** takes effect quickly instead of appearing
  to hang on a slow connection.

## [0.1.6] — 2026-06-06

### Fixed
- **macOS app no longer hangs on the loading screen.** On the notarized build, Apple's
  hardened runtime blocked the bundled Python engine from loading its own libraries
  (*"different Team IDs"*), so the backend never started. Added the
  `disable-library-validation` entitlement so the engine loads correctly. Windows was
  unaffected.

## [0.1.5] — 2026-06-06

### Added
- **macOS build** — Apple Silicon, Apple-notarized (opens with no Gatekeeper warning).
- **"Check for updates" button in Settings**, alongside the automatic once-a-day check.
- **"Report this" button on the crash screen**, so a bug can be filed even if the app
  has errored out and the normal report button is gone.
- App **version is now shown in Settings**.

### Changed
- Automatic update checks are now **throttled to once per day** (previously on every
  launch), so the update feed reflects roughly one ping per active install per day.

### Fixed
- **Windows auto-update** no longer fails with *"Error opening file for writing…
  filingforge-api.exe"*. The installer now stops the engine sidecar before replacing
  files, so in-place updates complete cleanly.

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
