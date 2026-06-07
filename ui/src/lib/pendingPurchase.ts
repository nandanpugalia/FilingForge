// A pending Concall Decoder purchase, persisted across app restarts so a buyer who
// closed the app mid-pay can resume (poll / paste-code) instead of being stranded.
// Just the session UUID under one localStorage key — no secrets, no PII.
const KEY = "ff_pending_concall";

export function setPending(session: string): void {
  try { localStorage.setItem(KEY, session); } catch { /* storage blocked — non-fatal */ }
}

export function getPending(): string | null {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function clearPending(): void {
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
}
