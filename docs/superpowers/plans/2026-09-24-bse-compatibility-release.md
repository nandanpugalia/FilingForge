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

- [ ] Push the release branch; open and attach its PR; merge after review and all CI jobs pass.
- [ ] Tag the merge as `v0.1.20-beta1`; await both installers, Windows upgrade/BSE check and Apple notarization/stapling.
- [ ] Verify hashes, updater signatures, Mac Developer ID/Gatekeeper and DMG stapling.
- [ ] Exercise the real Mac updater from 0.1.19 to 0.1.20, new company search and existing-library refresh. Use temporary test documents and confirm existing saved documents remain intact.

## 4. Deliver to users

- [ ] Promote the exact tested beta artifacts to stable without rebuilding.
- [ ] Verify GitHub Latest and `latest.json` report 0.1.20 with working platform artifacts; verify both website download redirects.
- [ ] Record release evidence here and update the private live-status tracker. State any platform or environment limits accurately.
