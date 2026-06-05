import { API_BASE } from "./config";
import * as self from "./api";
import type { Candidate, BuildScope, JobStatus, LibraryItem, ProgressEvent, ImportedSkill } from "./types";

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
  const res = await safeFetch(`${API_BASE}/resolve`, jsonPost({ company }));
  if (!res.ok) return friendly(res);
  return (await res.json()).candidates as Candidate[];
}
export async function startBuild(scope: BuildScope): Promise<string> {
  const res = await safeFetch(`${API_BASE}/build`, jsonPost(scope));
  if (!res.ok) return friendly(res);
  return (await res.json()).job_id as string;
}
export async function getStatus(jobId: string): Promise<JobStatus> {
  const res = await safeFetch(`${API_BASE}/build/${jobId}`);
  if (!res.ok) return friendly(res);
  return (await res.json()) as JobStatus;
}
export async function getLibrary(root: string): Promise<LibraryItem[]> {
  const res = await safeFetch(`${API_BASE}/library?root=${encodeURIComponent(root)}`);
  if (!res.ok) return friendly(res);
  return (await res.json()).companies as LibraryItem[];
}
export async function getSkills(): Promise<ImportedSkill[]> {
  const res = await safeFetch(`${API_BASE}/skills`);
  if (!res.ok) return friendly(res);
  return (await res.json()).skills as ImportedSkill[];
}
export async function importSkill(path: string): Promise<ImportedSkill> {
  const res = await safeFetch(`${API_BASE}/skills/import`, jsonPost({ path }));
  if (!res.ok) return friendly(res);
  return (await res.json()).skill as ImportedSkill;
}
export async function openFolder(path: string): Promise<void> {
  const res = await safeFetch(`${API_BASE}/open-folder`, jsonPost({ path }));
  if (!res.ok) return friendly(res);
}

export interface BuildSubscription { close(): void; }
interface SubHandlers {
  onProgress: (e: ProgressEvent) => void;
  onEnd: (tail: { status?: string; result?: unknown; error?: string | null }) => void;
}

export function subscribeBuildEvents(jobId: string, h: SubHandlers): BuildSubscription {
  const es = new EventSource(`${API_BASE}/build/${jobId}/events`);
  let lastTail: { status?: string; result?: unknown; error?: string | null } | null = null;
  let settled = false;
  const settle = (tail: typeof lastTail) => { if (settled) return; settled = true; es.close(); h.onEnd(tail ?? {}); };
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
  return { close: () => { settled = true; es.close(); } };
}
