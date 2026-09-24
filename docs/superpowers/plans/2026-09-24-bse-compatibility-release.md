# BSE compatibility release implementation plan

> Execute this authorized maintenance release in the current session, with independent review before merging and native packaged-app checks before stable promotion.

**Goal:** Deliver the verified BSE request-header fix in FilingForge v0.1.20 to Mac and Windows users.

**Architecture:** Preserve commit `12040a9` and the shared `BSEClient` network boundary. Package it through the existing signed beta-to-stable path. Add a Windows release check for the affected search and preview operations and verify that the checked listener belongs to the installed app.

**Tech stack:** Python/httpx/FastAPI, React/Tauri, PowerShell, GitHub Actions.

## 1. Verify the existing repair

- [x] Independently reproduce released headers failing and updated headers succeeding against BSE.
- [x] Verify HCC, PFC and Tanla histories; build and refresh a temporary HCC library.
- [x] Trace API, MCP and sidecar BSE requests back to `BSEClient`.
- [x] Complete independent code and release review.

## 2. Prepare release metadata and checks

Files: `ui/package.json`, `ui/package-lock.json`, `ui/src-tauri/tauri.conf.json`, `ui/src-tauri/Cargo.toml`, `ui/src-tauri/Cargo.lock`, `CHANGELOG.md`, `scripts/windows_upgrade_smoke.ps1`, `.github/workflows/release.yml`.

- [x] Set app/package/root lockfile versions from 0.1.19 to 0.1.20; move the existing unreleased BSE fix note under 0.1.20.
- [x] Have Windows validation identify the launched app's descendant-owned listener in ports 8765–8775, require an older installed baseline, and perform HCC search plus nonempty one-year financial-results preview with the new packaged engine.
- [x] Keep authenticated installer download separate from launching tested binaries, so the test process does not inherit the release token.
- [x] Run `.venv/bin/python -m pytest`, `.venv/bin/python scripts/test_check_release_version.py`, `.venv/bin/python scripts/check_release_version.py --tag v0.1.20-beta1`, UI lint, build and tests. Required outcome: all checks pass.

## 3. Build and verify the exact artifacts

- [x] Push the release branch; open and attach its PR; merge after review and all CI jobs pass.
- [x] Tag the merge as `v0.1.20-beta1`; await both installers, Windows upgrade/BSE check and Apple notarization/stapling.
- [x] Verify hashes, updater signatures, Mac Developer ID/Gatekeeper and DMG stapling.
- [x] Exercise the real Mac updater from 0.1.19 to 0.1.20, new company search and existing-library refresh. Use temporary test documents and confirm existing saved documents remain intact.

## 4. Deliver to users

- [x] Promote the exact tested beta artifacts to stable without rebuilding.
- [x] Verify GitHub Latest and `latest.json` report 0.1.20 with working platform artifacts; verify both website download redirects.
- [x] Record release evidence here and update the private live-status tracker. State any platform or environment limits accurately.

## Verification evidence — 24 September 2026

- [PR #26](https://github.com/nandanpugalia/FilingForge/pull/26) merged as `3a445bc6d1218d928c1b6e71aa0f9b85927d5999`. The header fix is shared by the CLI, API, MCP and desktop sidecar. The final TLS change also preserves `SSL_CERT_FILE` / `SSL_CERT_DIR` trust configuration.
- Source validation: 359 Python tests, 104 UI tests, five version-check tests, UI lint/build, and independent code/release review passed.
- [Release workflow](https://github.com/nandanpugalia/FilingForge/actions/runs/36018473688): both builds, Windows upgrade/BSE gate, Mac notarization/stapling, publish and beta-feed jobs passed.
- Windows CI: genuine 0.1.19 → 0.1.20 installer upgrade; the checked listener belonged to the launched app; HCC resolved to 500185 and preview returned four financial results.
- Windows workstation: actual installed 0.1.16 → 0.1.20 upgrade; HCC search/preview, four-file build and repeat refresh passed (0 downloads, 4 skipped, 0 failed). Saved filing hashes were unchanged.
- Mac: real 0.1.19 in-app updater installed 0.1.20. Developer ID signature, Gatekeeper notarization and stapled DMG validated. Both updater signatures verified and rejected tampered artifacts.
- Mac packaged engine: HCC four-file build and repeat refresh passed. Native desktop search returned HCC; scoped preview recognized all four existing filings. The Library Refresh button completed a one-year refresh with 87 ready filings: 83 new, 4 already held.
- All 1,425 files in the original Mac library remained byte-for-byte unchanged; original folder, five-year default and open-folder preference were restored after temporary-library testing.
- Desktop-control limitation: after the updater restarted the process, screen control could not find its window. A clean launch was used for the remaining native checks, which passed. Automatic window reappearance was not confirmed.
- [v0.1.20](https://github.com/nandanpugalia/FilingForge/releases/tag/v0.1.20-beta1) promoted from prerelease to stable without rebuilding. The tag retains `-beta1`; the release is stable. GitHub Latest and the stable updater feed report 0.1.20; both website download routes return HTTP 200 from this release.
- Notification routing: GitHub PR/issues/releases and release/stapling workflow notices use the reports channel; workflow failures use errors. The existing metrics hook retains only fork/star events. Dedicated report/error secrets are provisioned; there is no workflow fallback to metrics.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `FilingForge_aarch64.app.tar.gz` | `a93828130ce99f6afbfc7a6086e7a63bea3719de9893928114c4dbf93ebee87b` |
| `FilingForge_0.1.20_x64-setup.exe` | `607d3f93b913cba90a39c7302211dcff3d26ef94866dad1b89f024dc8ac6488d` |
