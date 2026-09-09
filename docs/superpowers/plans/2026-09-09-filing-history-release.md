# Filing history maintenance release

Goal: repair multi-year announcement retrieval and ship v0.1.19 through the existing signed beta-to-stable release path.

Design: use the released v0.1.18 code as the base. Split the existing inclusive years*365 range into windows with at most 365 days between endpoints; share boundaries and deduplicate by news ID. Preserve classification, archive merging and document recovery. Propagate network errors. No user setting or library migration is required.

- [x] Reproduce long-window failures live on Chembond and PFC.
- [x] Start an isolated branch from current GitHub main, preserving local-only work.
- [x] Run baseline tests, add failing window/pagination/boundary/error regression cases.
- [x] Integrate window retrieval and run the engine/API regression suite.
- [ ] Verify live Chembond, PFC, KFin and Tanla; verify an existing library remains unchanged during preview.
- [ ] Review code; align release versions and changelog; run UI/build and version checks.
- [ ] Push branch, merge after CI, build v0.1.19-beta1 installers.
- [ ] Verify signed artifacts, notarization, real upgrade and new/refresh library paths.
- [ ] Promote verified artifacts; verify stable feed and website redirect target.
