# BSE TLS compatibility release — 30 September 2026

Restore public Windows and macOS access to BSE after header changes alone stopped working.
The source fix is `b011dfd8563e065b5457604f186e4ee8bfc3cf20`; desktop version is 0.1.21.

## Source verification

- Test-first: 22 browser-transport regressions failed against the old HTTPX implementation;
  the injected offline transport passed. Certificate-store and packaging regressions also
  failed before the implementation changed.
- Focused transport and packaging tests: 43 passed.
- Full Python suite: 383 passed, 3 skipped; real pytest exit code 0.
- Explicit live HEG smoke: BSE 509631 resolved, one page returned 50 announcements,
  one 834,265-byte PDF downloaded and its magic verified; 1 passed, exit code 0.
- `python -m engine HEG /tmp/ffprobe --years 1`: 210 new filings, zero skipped,
  exit code 0. Verified 210 PDFs and both indexes, then removed the probe directory.
- [Source CI](https://github.com/nandanpugalia/FilingForge/actions/runs/36666490971): Python,
  MCP and UI tests passed, as did native Windows/macOS sidecar builds and startup checks.
- Independent transport review found no blockers.

## Public delivery

The public release uses `00af26a568ed7827ed4add4222f8365b572c5ed3`, adding quiet manual
release controls without changing the verified engine. Three notification guards were
observed failing before the workflow change, then passed; all five version tests and
[CI](https://github.com/nandanpugalia/FilingForge/actions/runs/36668080142) passed.
Independent workflow review found no blockers.

[Signed release run](https://github.com/nandanpugalia/FilingForge/actions/runs/36668121507)
created `v0.1.21-beta1` from that exact commit. All six jobs passed: Windows and Mac builds,
Windows upgrade smoke, Mac notarization/stapling, publishing, and updater-feed publishing.

## Packaged release verification

- Windows: genuine installer upgrade from 0.1.20 to 0.1.21 passed. The launched app's
  own packaged engine resolved HCC and previewed four financial results from BSE.
- Mac: Developer ID signature verification, Gatekeeper assessment and stapled DMG validation
  passed for the exact downloaded release. Both platform updater signatures verified;
  deliberately modified payloads were rejected.
- Mac packaged engine: health reported 0.1.21; HEG resolved to 509631; a one-year financial
  results preview found four filings. Building a temporary library downloaded all four
  with zero failures. Refresh downloaded zero, skipped four, and failed zero; all four
  saved PDF hashes were unchanged.
- Native Mac search returned HEG (509631), and Settings displayed v0.1.21. Existing library
  location, five-year default, open-folder preference and beta preference were not changed.
- The real Mac in-app updater installed 0.1.21 over 0.1.20. Desktop control could not find
  the window after restart, as in the previous release's QA. The idle process was quit and
  a clean launch reached the home screen, resolved HEG (509631) through the visible search,
  and displayed v0.1.21 in Settings. Automatic window reappearance was not confirmed.

## Stable delivery

- [FilingForge v0.1.21](https://github.com/nandanpugalia/FilingForge/releases/tag/v0.1.21-beta1)
  was promoted to stable without rebuilding. The retained tag ends in `-beta1`, but the
  release is neither draft nor prerelease and is GitHub Latest.
- The public stable `latest.json` reports 0.1.21 for Mac Apple Silicon and Windows x64,
  including both legacy and installer-specific platform keys.
- Both website download buttons redirect to the new release and return HTTP 200.
- All four workflow Discord notification steps were skipped. The repository webhook's
  release event was temporarily suppressed during publishing/promotion and restored
  afterward; its other event subscriptions were preserved. No Discord posts were made.
- No desk repository or server was changed, and the untracked `docs/audits/` was left alone.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `FilingForge_aarch64.app.tar.gz` | `449c264c4c64b1cf4658034d88bccc96fa1358b5d38a83de069142c58f54a2fc` |
| `FilingForge_0.1.21_x64-setup.exe` | `9886cf738d4efbd1cfbe2faaf039181834b18cba20dfd4481c8122e520353ca2` |
