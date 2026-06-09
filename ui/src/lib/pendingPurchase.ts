// A pending Concall Decoder purchase, persisted across app restarts so a buyer who
// closed the app mid-pay can resume (reopen the payment page / poll / paste-code)
// instead of being stranded. Session UUID + the checkout URL — no secrets, no PII.
const KEY = "ff_pending_concall";          // session uuid (kept as a bare string for back-compat)
const URL_KEY = "ff_pending_concall_url";  // the Razorpay checkout URL, so "Continue" can reopen it
const SKILL_KEY = "ff_pending_skill";      // which paid SKU this pending purchase is for (id)
const NAME_KEY = "ff_pending_skill_name";  // its display name, so resume/install label it right

export function setPending(session: string, url?: string, skillId?: string, name?: string): void {
  try {
    localStorage.setItem(KEY, session);
    if (url) localStorage.setItem(URL_KEY, url);
    if (skillId) localStorage.setItem(SKILL_KEY, skillId);
    if (name) localStorage.setItem(NAME_KEY, name);
  } catch { /* storage blocked — non-fatal */ }
}

export function getPending(): string | null {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function getPendingUrl(): string | null {
  try { return localStorage.getItem(URL_KEY); } catch { return null; }
}

// Which skill the pending purchase is for (id + display name). Null for legacy/absent.
export function getPendingSkill(): { id: string | null; name: string | null } {
  try { return { id: localStorage.getItem(SKILL_KEY), name: localStorage.getItem(NAME_KEY) }; }
  catch { return { id: null, name: null }; }
}

export function clearPending(): void {
  try {
    localStorage.removeItem(KEY); localStorage.removeItem(URL_KEY);
    localStorage.removeItem(SKILL_KEY); localStorage.removeItem(NAME_KEY);
  } catch { /* ignore */ }
}
