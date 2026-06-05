import { it, expect } from "vitest";
import { shouldAutoCheck, UPDATE_CHECK_INTERVAL_MS } from "../lib/useUpdate";

// The updater fetches latest.json on each auto-check, which GitHub counts as a "ping"
// (our privacy-clean active-install signal). Throttling the auto-check to once/24h keeps
// that to ~1 ping/day/install instead of 1/launch, so the metric isn't inflated.
it("auto-checks only when never checked, or >= 24h since the last check", () => {
  const now = 1_700_000_000_000;
  expect(shouldAutoCheck(null, now)).toBe(true);                                   // never checked
  expect(shouldAutoCheck(now - UPDATE_CHECK_INTERVAL_MS, now)).toBe(true);         // exactly 24h ago
  expect(shouldAutoCheck(now - (UPDATE_CHECK_INTERVAL_MS + 60_000), now)).toBe(true);  // >24h
  expect(shouldAutoCheck(now - (UPDATE_CHECK_INTERVAL_MS - 60_000), now)).toBe(false); // just under 24h
  expect(shouldAutoCheck(now - 60_000, now)).toBe(false);                          // 1 min ago → skip
  expect(shouldAutoCheck(now, now)).toBe(false);                                   // just now → skip
});
