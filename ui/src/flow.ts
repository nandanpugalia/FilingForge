import type { Candidate, ProgressEvent, BuildResult } from "./types";

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
  | { type: "FAIL"; message: string }
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
    case "FAIL": return { ...s, phase: "error", error: a.message };
    case "RESET": return { ...initialState };
    default: return s;
  }
}
