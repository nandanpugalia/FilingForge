#!/usr/bin/env bash
# make-release.sh — build a signed FilingForge release and assemble the updater feed.
#
# Run this ON EACH OS (macOS builds the darwin entry; Windows via Git-Bash builds the
# windows entry). It merges into release/feed/latest.json, so after running on both
# machines (and copying their feed files together) you have one feed serving both.
#
# Requires the updater PRIVATE key (kept in 1Password / ~/.filingforge/updater.key — NEVER
# in the repo). Set it (as the key STRING) + password via env before running:
#   export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.filingforge/updater.key)"
#   export TAURI_SIGNING_PRIVATE_KEY_PASSWORD=""          # empty if the key has no password
#   export FF_FEED_BASE="https://filingforge-updates.pages.dev"   # where the feed is hosted
#
# Usage:  bash scripts/make-release.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UI="$ROOT/ui"
FEED="$ROOT/release/feed"
CONF="$UI/src-tauri/tauri.conf.json"
mkdir -p "$FEED"

: "${TAURI_SIGNING_PRIVATE_KEY:?set TAURI_SIGNING_PRIVATE_KEY to the updater private key string (from 1Password): export TAURI_SIGNING_PRIVATE_KEY=\"\$(cat ~/.filingforge/updater.key)\"}"
export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:-}"
FEED_BASE="${FF_FEED_BASE:-https://filingforge-updates.pages.dev}"

VERSION="$(python3 -c "import json,sys;print(json.load(open('$CONF'))['version'])")"
echo "▸ Building FilingForge v$VERSION (signed)…"

( cd "$UI" && npx tauri build )

BUNDLE="$UI/src-tauri/target/release/bundle"
OS="$(uname -s)"
case "$OS" in
  Darwin)
    ARCH="$(uname -m)"; [ "$ARCH" = "arm64" ] && PLAT="darwin-aarch64" || PLAT="darwin-x86_64"
    ART="$(ls "$BUNDLE"/macos/*.app.tar.gz | head -1)"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    PLAT="windows-x86_64"
    ART="$(ls "$BUNDLE"/nsis/*-setup.nsis.zip 2>/dev/null | head -1 || ls "$BUNDLE"/msi/*.msi.zip | head -1)"
    ;;
  *) echo "Unsupported OS: $OS" >&2; exit 1 ;;
esac

SIG="$(cat "${ART}.sig")"
ARTNAME="$(basename "$ART")"
cp "$ART" "$FEED/"
echo "▸ $PLAT artifact: $ARTNAME"

# Merge this platform into latest.json (create if absent).
python3 - "$FEED/latest.json" "$VERSION" "$PLAT" "$FEED_BASE/$ARTNAME" "$SIG" <<'PY'
import json, sys, os, datetime
path, version, plat, url, sig = sys.argv[1:6]
data = {"version": version, "notes": "See the release notes.",
        "pub_date": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platforms": {}}
if os.path.exists(path):
    try: data = json.load(open(path))
    except Exception: pass
data["version"] = version
data.setdefault("platforms", {})[plat] = {"signature": sig, "url": url}
json.dump(data, open(path, "w"), indent=2)
print("▸ wrote", path)
PY

echo "✅ Done. Upload the contents of release/feed/ to $FEED_BASE :"
ls -1 "$FEED"
echo "   The app's endpoint (tauri.conf.json) must point at $FEED_BASE/latest.json"
