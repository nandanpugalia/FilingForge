# Filing history maintenance release

Goal: repair multi-year announcement retrieval and ship v0.1.19 through the existing signed beta-to-stable release path.

Design: use the released v0.1.18 code as the base. Split the existing inclusive years*365 range into windows with at most 365 days between endpoints; share boundaries and deduplicate by news ID. Preserve classification, archive merging and document recovery. Propagate network errors. No user setting or library migration is required.

- [x] Reproduce long-window failures live on Chembond and PFC.
- [x] Start an isolated branch from current GitHub main, preserving local-only work.
- [x] Run baseline tests, add failing window/pagination/boundary/error regression cases.
- [x] Integrate window retrieval and run the engine/API regression suite.
- [x] Verify live Chembond, PFC, KFin and Tanla; verify an existing library remains unchanged during preview.
- [x] Review code; align release versions and changelog; run UI/build and version checks.
- [x] Push branch, merge after CI, build v0.1.19-beta1 installers.
- [x] Verify signed artifacts, notarization, real upgrade and new/refresh library paths.
- [x] Promote verified artifacts; verify stable feed and website redirect target.

## Release verification — complete

Stable v0.1.19 was promoted from the exact v0.1.19-beta1 artifacts without rebuilding.
PR: https://github.com/nandanpugalia/FilingForge/pull/25
Release run: https://github.com/nandanpugalia/FilingForge/actions/runs/34380588377

- 355 local Python tests passed; 2 optional/live tests skipped. All GitHub Python, MCP and UI jobs passed. 104 UI tests passed, as did lint, build and release-version checks.
- Regression tests failed before the windowing fix. Independent review checked the retrieval logic and Windows upgrade gate.
- Live curated previews: Chembond 107 filings over six years, PFC 116 over five, KFin 155 over five, Tanla 69 over two.
- The installed Mac app upgraded through the real signed beta updater from 0.1.18 to 0.1.19 and restarted. The same six-year Chembond request changed from six annual reports to 107 filings.
- Mac Developer ID signature, Gatekeeper acceptance and DMG stapling validated.
- Windows CI installed stable 0.1.18, launched it and checked engine health, installed 0.1.19 over it, checked the executable version, and launched the new app with a healthy engine. This tests installer replacement; the Mac test exercises the separate in-app updater flow.
- Packaged engine: three real documents downloaded/converted, refresh skipped all three, Stop saved a complete document, and forced engine termination followed by restart recovered successfully without partial files.
- Existing-library preview recognised 168 saved Tanla filings and 26 new ones. Checksums of 3,937 existing user-library files matched after the Mac update.
- Stable updater feed reports 0.1.19 with both platform artifacts reachable. Both website download routes resolve to the promoted release.
