import type { Candidate } from "../types";
// Prefer the real BSE trading symbol (engine R0); fall back to first word only if absent.
export function tickerFor(c: Candidate): string {
  return (c.symbol && c.symbol.trim()) ? c.symbol.trim().toUpperCase()
       : c.company.split(" ")[0].toUpperCase();
}
