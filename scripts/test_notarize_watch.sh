#!/usr/bin/env bash
# Unit tests for notarize_watch.sh's pure decision logic (classify_status).
# Run: bash scripts/test_notarize_watch.sh
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$DIR/notarize_watch.sh"   # no args -> defines functions, does not poll

fails=0
expect() { # expect <input> <want>
  got="$(classify_status "$1")"
  if [ "$got" != "$2" ]; then echo "FAIL classify_status('$1') = '$got', want '$2'"; fails=$((fails+1));
  else echo "ok    classify_status('$1') = '$got'"; fi
}

expect "Accepted"     success
expect "Invalid"      fail
expect "Rejected"     fail
expect "In Progress"  wait
expect "Pending"      wait
expect ""             wait        # no/empty response (e.g. a network blip) must be 'wait', never fatal
expect "Weirdness"    unknown     # unexpected -> wait-equivalent (keep polling), not crash

echo "---"
if [ "$fails" -eq 0 ]; then echo "ALL PASS"; else echo "$fails FAILED"; exit 1; fi
