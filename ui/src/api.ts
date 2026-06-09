import * as self from "./api";
import { isTauri } from "./components/ReadyGate";
import { WORKER_URL } from "./config";
import type { Candidate, BuildScope, JobStatus, LibraryItem, ProgressEvent, ImportedSkill, PreviewResult } from "./types";

// ── Source of truth for the engine URL ──────────────────────────────────────
// The Rust shell picks a free port at launch (8765, or 8766 if taken …) and
// exposes it via the `engine_info` Tauri command. Everything below routes
// through apiBase() so a non-default port can never silently break the app.
let _engine: { port: number; token: string } | null = null;
export async function engineInfo(): Promise<{ port: number; token: string }> {
  if (_engine) return _engine;
  if (!isTauri()) return (_engine = { port: 8765, token: "" });
  const { invoke } = await import("@tauri-apps/api/core");
  return (_engine = await invoke<{ port: number; token: string }>("engine_info"));
}

let _baseUrl: string | null = null;
export async function apiBase(): Promise<string> {
  if (_baseUrl) return _baseUrl;
  if (!isTauri()) return (_baseUrl = "http://127.0.0.1:8765");
  const { port } = await engineInfo();
  return (_baseUrl = `http://127.0.0.1:${port}`);
}

// Build a token-gated URL to a served library file (report HTML, cited PDFs).
export async function reportUrl(relPath: string): Promise<string> {
  const e = await engineInfo();
  const base = await apiBase();
  const q = e.token ? `?token=${encodeURIComponent(e.token)}` : "";
  // relPath is already posix (forward slashes), root-relative, e.g. "ACME/research_report/business_model.html".
  // Encode each segment (keeping the slashes) so a '#'/'?'/'%'/space in a ticker or filename can't break the URL.
  const safeRel = relPath.split("/").map(encodeURIComponent).join("/");
  return `${base}/lib/${safeRel}${q}`;
}

async function safeFetch(input: string, init?: RequestInit): Promise<Response> {
  try { return await fetch(input, init); }
  catch { throw new Error("Hmm — couldn't reach the engine. Give it a second and try again."); }
}
async function friendly(res: Response): Promise<never> {
  let msg = "Something went wrong. Please try again.";
  try { const b = await res.json(); if (b?.user_message) msg = b.user_message; } catch { /* ignore */ }
  throw new Error(msg);
}
const jsonPost = (body: unknown): RequestInit =>
  ({ method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });

export async function resolve(company: string): Promise<Candidate[]> {
  const res = await safeFetch(`${await apiBase()}/resolve`, jsonPost({ company }));
  if (!res.ok) return friendly(res);
  return (await res.json()).candidates as Candidate[];
}
export async function previewBuild(scope: BuildScope): Promise<PreviewResult> {
  // List-only: how many filings this scope would pull (by category) + how many already have.
  const res = await safeFetch(`${await apiBase()}/preview`, jsonPost(scope));
  if (!res.ok) return friendly(res);
  return (await res.json()) as PreviewResult;
}
export async function startBuild(scope: BuildScope): Promise<string> {
  const res = await safeFetch(`${await apiBase()}/build`, jsonPost(scope));
  if (!res.ok) return friendly(res);
  return (await res.json()).job_id as string;
}
export async function cancelBuild(jobId: string): Promise<void> {
  const res = await safeFetch(`${await apiBase()}/build/${jobId}/cancel`, { method: "POST" });
  if (!res.ok) return friendly(res);
}
export async function getStatus(jobId: string): Promise<JobStatus> {
  const res = await safeFetch(`${await apiBase()}/build/${jobId}`);
  if (!res.ok) return friendly(res);
  return (await res.json()) as JobStatus;
}
export async function getLibrary(root: string): Promise<LibraryItem[]> {
  const res = await safeFetch(`${await apiBase()}/library?root=${encodeURIComponent(root)}`);
  if (!res.ok) return friendly(res);
  return (await res.json()).companies as LibraryItem[];
}
export async function getSkills(): Promise<ImportedSkill[]> {
  const res = await safeFetch(`${await apiBase()}/skills`);
  if (!res.ok) return friendly(res);
  return (await res.json()).skills as ImportedSkill[];
}
export async function importSkill(path: string): Promise<ImportedSkill> {
  const res = await safeFetch(`${await apiBase()}/skills/import`, jsonPost({ path }));
  if (!res.ok) return friendly(res);
  return (await res.json()).skill as ImportedSkill;
}
// Install a skill that arrived as md TEXT (a paid pack fetched from the Worker) — goes to
// the engine sidecar (~/.filingforge/skills/) so it appears in getSkills() like an import.
export async function installSkillMd(name: string, content: string): Promise<ImportedSkill> {
  const res = await safeFetch(`${await apiBase()}/skills/install`, jsonPost({ name, content }));
  if (!res.ok) return friendly(res);
  return (await res.json()).skill as ImportedSkill;
}

// ── Payments Worker (Razorpay) — premium skill buy flow ──────────────────────
// These hit the WORKER, not the engine sidecar. The Worker holds the Razorpay
// secret and is the source of truth; the app only ever sees the watermarked .md.
const newSession = (): string =>
  (crypto.randomUUID ? crypto.randomUUID()
    : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
      }));

// Generate a session, ask the Worker for a payment link. Returns both so the caller can
// persist the session (resume/paste-code) and open the URL in the browser. `email` (when valid)
// is carried onto the link so the buyer gets the receipt + skill .md. `skill` selects which paid
// SKU (the Worker validates price server-side); omit it and the Worker defaults to the original
// skill, so older callers keep working.
export async function startCheckout(email?: string, skill?: string): Promise<{ url: string; session: string }> {
  const session = newSession();
  const res = await safeFetch(`${WORKER_URL}/checkout`, jsonPost({ session, email, skill }));
  if (!res.ok) throw new Error("Couldn't start checkout. Please try again in a moment.");
  const url = (await res.json())?.url as string | undefined;
  if (!url) throw new Error("Couldn't start checkout. Please try again in a moment.");
  return { url, session };
}

export type RedeemResult =
  | { status: "ready"; md: string }       // 200 — the watermarked skill .md
  | { status: "pending" }                 // 202 — paid not yet seen / still processing
  | { status: "notfound" };               // 403/404 — refunded, cap hit, or unknown code

// Poll/redeem by session. 200 → md text; 202 → pending; 403/404 → friendly "not found".
export async function redeem(session: string): Promise<RedeemResult> {
  try {
    const res = await fetch(`${WORKER_URL}/redeem?session=${encodeURIComponent(session)}`);
    if (res.status === 202) return { status: "pending" };
    if (res.status === 403 || res.status === 404) return { status: "notfound" };
    if (!res.ok) return { status: "pending" };
    // res.text() must stay INSIDE the try: macOS WKWebView can error the body stream
    // (e.g. on an attachment-disposition response). Degrade to pending, never hard-throw.
    return { status: "ready", md: await res.text() };
  } catch {
    // offline / network blip / body-read error — treat as pending so the caller keeps polling.
    return { status: "pending" };
  }
}

// Webhook-loss insurance: reconcile straight from Razorpay using the payment id.
export async function redeemFallback(session: string, paymentId: string): Promise<RedeemResult> {
  try {
    const res = await fetch(`${WORKER_URL}/redeem-fallback`, jsonPost({ session, payment_id: paymentId }));
    if (res.status === 403 || res.status === 404) return { status: "notfound" };
    if (!res.ok) return { status: "pending" };
    return { status: "ready", md: await res.text() };   // body read inside try (see redeem())
  } catch {
    return { status: "pending" };
  }
}
export async function openFolder(path: string): Promise<void> {
  const res = await safeFetch(`${await apiBase()}/open-folder`, jsonPost({ path }));
  if (!res.ok) return friendly(res);
}

export interface BuildSubscription { close(): void; }
interface SubHandlers {
  onProgress: (e: ProgressEvent) => void;
  onEnd: (tail: { status?: string; result?: unknown; error?: string | null }) => void;
}

export function subscribeBuildEvents(jobId: string, h: SubHandlers): BuildSubscription {
  let es: EventSource | null = null;
  let closed = false;
  let lastTail: { status?: string; result?: unknown; error?: string | null } | null = null;
  let settled = false;
  const settle = (tail: typeof lastTail) => { if (settled) return; settled = true; es?.close(); h.onEnd(tail ?? {}); };
  // Resolve the runtime engine base first, then wire up the EventSource.
  apiBase().then((base) => {
    if (closed) return;
    es = new EventSource(`${base}/build/${jobId}/events`);
    es.onmessage = (ev: MessageEvent) => {
      let data: { percent?: number; stage?: string; status?: string } | undefined;
      try { data = JSON.parse(ev.data); } catch { return; }   // ignore "end"/keep-alives
      if (data && typeof data.percent === "number" && "stage" in data) h.onProgress(data as ProgressEvent);
      else if (data && "status" in data) lastTail = data;     // terminal frame keyed on `status`
    };
    es.addEventListener("end", () => settle(lastTail));
    es.onerror = async () => {                                 // normal close OR transient drop
      if (settled) return;
      try {
        // route through the module namespace so vi.spyOn(api, "getStatus") intercepts it
        const st = await self.getStatus(jobId);
        if (st.status === "done" || st.status === "error") settle({ status: st.status, result: st.result, error: st.error });
        // else queued/running → transient; EventSource auto-reconnects, do nothing
      } catch { settle(lastTail); }
    };
  });
  return { close: () => { closed = true; settled = true; es?.close(); } };
}
