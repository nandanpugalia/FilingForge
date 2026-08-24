import type { Candidate, ProgressEvent, BuildResult, PendingDocument } from "./types";

export type Phase = "search" | "configure" | "building" | "done" | "error";

export interface State {
  phase: Phase;
  company: Candidate | null;
  jobId: string | null;
  progress: ProgressEvent | null;
  progressLog: string[];
  result: BuildResult | null;
  error: string | null;
}

export const initialState: State = {
  phase: "search", company: null, jobId: null, progress: null, progressLog: [], result: null, error: null,
};

export type Action =
  | { type: "PICK_COMPANY"; candidate: Candidate }
  | { type: "CHANGE_COMPANY" }
  | { type: "START_BUILD"; jobId: string }
  | { type: "PROGRESS"; progress: ProgressEvent }
  | { type: "BUILD_DONE"; result: BuildResult }
  | { type: "PENDING_IMPORTED"; pending: PendingDocument[] }
  | { type: "FAIL"; message: string }
  | { type: "BACK_TO_CONFIGURE" }
  | { type: "RESET" };

const LOG_CAP = 200;

export function reducer(s: State, a: Action): State {
  switch (a.type) {
    case "PICK_COMPANY": return { ...s, phase: "configure", company: a.candidate, error: null };
    case "CHANGE_COMPANY": return { ...initialState };
    case "START_BUILD": return { ...s, phase: "building", jobId: a.jobId, progress: null, progressLog: [], error: null };
    case "PROGRESS":
      return s.phase === "building"
        ? { ...s, progress: a.progress, progressLog: [...s.progressLog, a.progress.message].slice(-LOG_CAP) }
        : s;
    case "BUILD_DONE": return s.phase === "building" ? { ...s, phase: "done", result: a.result } : s;
    case "PENDING_IMPORTED":
      return s.phase === "done" && s.result
        ? { ...s, result: { ...s.result, downloaded: s.result.downloaded + 1, pending: a.pending } }
        : s;
    case "FAIL": return { ...s, phase: "error", error: a.message };
    case "BACK_TO_CONFIGURE":
      // Only from building/error, and only if we still know which company.
      return (s.phase === "building" || s.phase === "error") && s.company
        ? { ...s, phase: "configure", jobId: null, progress: null, progressLog: [], error: null }
        : s;
    case "RESET": return { ...initialState };
    default: return s;
  }
}
