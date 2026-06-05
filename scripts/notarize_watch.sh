#!/usr/bin/env bash
# notarize_watch.sh — async Apple notarization watcher + stapler.
#
# WHY THIS EXISTS: tauri-action notarizes synchronously (`notarytool submit --wait`),
# which blocks the macOS build runner for the full ~2-3.5h Apple queue. A single
# transient network hiccup on the runner (we hit one at 1h52m: "Resolved 0 endpoints…
# No network route") kills the entire 2-hour build with a misleading "Internet
# connection appears to be offline." This decouples it: the BUILD job submits without
# waiting and walks away; THIS script runs in a separate cheap job that polls Apple and
# tolerates transient errors (a blip just retries the next poll instead of nuking the run),
# then staples the ticket into the DMG so even offline first-launch is clean.
#
# Usage:
#   notarize_watch.sh <submission_id> <dmg_path> [more_dmg_paths...]
# Env required: APPLE_ID, APPLE_TEAM_ID, APPLE_PASSWORD (app-specific password)
# Optional env: NOTARIZE_MAX_MINUTES (default 240), NOTARIZE_POLL_SECONDS (default 60)
#
# Exit codes: 0 = Accepted (+ stapled if DMGs given); 1 = Rejected/Invalid; 2 = timeout/poll error.
set -uo pipefail

# classify_status: pure decision from a notarytool status string -> one of: success | fail | wait | unknown
# Isolated so it can be unit-tested without hitting Apple (see scripts/test_notarize_watch.sh).
classify_status() {
  case "$1" in
    Accepted)               echo "success" ;;
    Invalid|Rejected)       echo "fail" ;;
    "In Progress"|Pending|"") echo "wait" ;;
    *)                      echo "unknown" ;;
  esac
}

# Only run the live watcher when invoked directly with args — sourcing the file (for tests)
# defines classify_status without polling Apple.
if [ "${BASH_SOURCE[0]}" = "${0}" ] && [ "$#" -ge 1 ]; then
  SUBMISSION_ID="$1"; shift
  DMGS=("$@")
  MAX_MINUTES="${NOTARIZE_MAX_MINUTES:-240}"
  POLL_SECONDS="${NOTARIZE_POLL_SECONDS:-60}"
  : "${APPLE_ID:?APPLE_ID required}"; : "${APPLE_TEAM_ID:?APPLE_TEAM_ID required}"; : "${APPLE_PASSWORD:?APPLE_PASSWORD required}"

  deadline=$(( $(date +%s) + MAX_MINUTES * 60 ))
  echo "Watching notarization $SUBMISSION_ID (timeout ${MAX_MINUTES}m, poll ${POLL_SECONDS}s)…"
  while :; do
    raw=$(xcrun notarytool info "$SUBMISSION_ID" \
            --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD" \
            --output-format json 2>/dev/null) || raw=""
    status=$(printf '%s' "$raw" | python3 -c "import sys,json;\
print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    verdict=$(classify_status "$status")
    echo "  $(date -u +%H:%M:%S) status='${status:-<no response>}' -> $verdict"

    case "$verdict" in
      success)
        echo "Notarization Accepted."
        for dmg in "${DMGS[@]:-}"; do
          [ -n "$dmg" ] && [ -f "$dmg" ] || { echo "  (skip staple, not a file: $dmg)"; continue; }
          echo "  Stapling $dmg"
          xcrun stapler staple "$dmg" && xcrun stapler validate "$dmg"
        done
        exit 0 ;;
      fail)
        echo "Notarization $status — fetching log:"; \
        xcrun notarytool log "$SUBMISSION_ID" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD" 2>/dev/null || true
        exit 1 ;;
      wait|unknown)
        : ;;  # transient error, empty, or still queued — keep polling (blip-immune)
    esac

    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "Timed out after ${MAX_MINUTES}m still '${status:-<no response>}'. Release already published; staple can be retried."
      exit 2
    fi
    sleep "$POLL_SECONDS"
  done
fi
