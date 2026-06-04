import { API_BASE } from "./config";
import type { Candidate, BuildScope, JobStatus, LibraryItem } from "./types";

async function safeFetch(input: string, init?: RequestInit): Promise<Response> {
  try { return await fetch(input, init); }
  catch { throw new Error("FilingForge isn't running yet. Start the app's engine and try again."); }
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
export async function openFolder(path: string): Promise<void> {
  const res = await safeFetch(`${API_BASE}/open-folder`, jsonPost({ path }));
  if (!res.ok) return friendly(res);
}
