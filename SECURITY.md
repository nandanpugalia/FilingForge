# Security Policy

Thanks for helping keep FilingForge and its users safe. Security reports are
taken seriously even though this is a small, indie open-source project.

## Reporting a vulnerability

**Please report vulnerabilities privately through GitHub.** Do not open a public
issue for a security problem.

Go to the repository's **Security** tab → **"Report a vulnerability"** to open a
private security advisory. This routes the report straight to the maintainers and
keeps the details confidential until a fix is available. We don't currently offer a
PGP key — GitHub's private advisory channel is already encrypted in transit.

When you report, it helps to include:

- A clear description of the issue and its impact.
- Steps to reproduce (a proof of concept is ideal).
- The affected version, and your OS (macOS / Windows + version).

## Response expectations

This is a best-effort indie project. We aim to **acknowledge your report within a
few days**, and will keep you updated as we investigate and work on a fix. If you
don't hear back, a gentle nudge on the advisory is welcome.

## Supported versions

Security fixes target the **latest released version**; we don't backport fixes to
older releases. Please make sure you can reproduce the issue on the most recent
release before reporting.

## Threat model — what's worth reporting

FilingForge is **local-first**: it runs entirely on the user's machine, the engine
never calls an LLM, and no user data leaves the computer. That said, the parts of
the architecture below are the most security-relevant and are squarely in scope:

- **The local loopback HTTP service.** The bundled Python engine runs a FastAPI
  service on `127.0.0.1:8765`. Anything that lets another local process or a web
  page abuse it is in scope: CORS/origin-validation gaps, **drive-by web attacks**
  (a malicious site the user visits making background cross-origin requests to the
  local port to read the library or trigger downloads), unauthenticated
  state-changing endpoints, path traversal into the user's library, or SSRF.
  *(We restrict the origins allowed to call the service to the app's own webview
  and dev origins — reports of a bypass are especially welcome.)*
- **Code-signed auto-updates.** The app ships updates signed with the Tauri updater
  key and checks them on launch. Issues that could undermine update integrity —
  signature/verification bypass, downgrade attacks, or MITM of the update feed —
  are in scope. *(This is the Tauri update-signing key. The Windows installer itself
  is not yet Authenticode-signed — that's why SmartScreen shows an "unrecognized
  publisher" notice; macOS notarization is in progress.)*
- **Sidecar binary integrity.** The engine ships as a PyInstaller-frozen binary on
  disk. A same-user process could replace it before launch; we rely on OS code
  signing (and macOS notarization, once available) to mitigate. Weaknesses here
  are worth reporting.
- **Port squatting.** If a local process binds `127.0.0.1:8765` before the engine
  starts, it could intercept the app's requests. Reports of insufficient
  port-conflict handling are in scope.
- **Dependency supply chain.** We pin dependencies in lockfiles, but a compromised
  PyPI/npm dependency is a realistic risk worth flagging.

Also welcome: anything that could lead to arbitrary file read/write outside the
library, code execution, leaking local data off the machine, or the library being
written world-readable on a shared machine.

Out of scope: vulnerabilities in third-party filings/PDFs themselves, and reports
that require an attacker who already has full root/admin control of the machine
(same-user binary replacement, noted above, is a known limitation we'd still like
to hear about).

Thank you for reporting responsibly.
