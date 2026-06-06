import * as self from "./api";
import { isTauri } from "./components/ReadyGate";
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
