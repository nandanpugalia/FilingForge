// A pending Concall Decoder purchase, persisted across app restarts so a buyer who
// closed the app mid-pay can resume (reopen the payment page / poll / paste-code)
// instead of being stranded. Session UUID + the checkout URL — no secrets, no PII.
const KEY = "ff_pending_concall";          // session uuid (kept as a bare string for back-compat)
const URL_KEY = "ff_pending_concall_url";  // the Razorpay checkout URL, so "Continue" can reopen it

export function setPending(session: string, url?: string): void {
  try {
    localStorage.setItem(KEY, session);
    if (url) localStorage.setItem(URL_KEY, url);
  } catch { /* storage blocked — non-fatal */ }
}

export function getPending(): string | null {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function getPendingUrl(): string | null {
  try { return localStorage.getItem(URL_KEY); } catch { return null; }
}

export function clearPending(): void {
  try { localStorage.removeItem(KEY); localStorage.removeItem(URL_KEY); } catch { /* ignore */ }
}
