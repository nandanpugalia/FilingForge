export interface Candidate { scrip_code: string; company: string; is_primary: boolean; isin?: string | null; symbol?: string | null; }
export interface BuildScope { scrip_code: string; ticker: string; dest: string; years: number; everything: boolean; categories: string[]; }
export interface ProgressEvent { stage: string; current: number; total: number; message: string; percent: number; }
export interface BuildResult { downloaded: number; skipped: number; failed: number; cancelled?: boolean; }
export interface JobStatus { job_id: string; status: "queued" | "running" | "done" | "cancelled" | "error"; progress: ProgressEvent | null; result: BuildResult | null; error: string | null; }
export interface PreviewCategory { label: string; count: number; }
export interface PreviewResult { total: number; new: number; have: number; by_category: PreviewCategory[]; }
export interface LibraryItem { ticker: string; total: number; counts: Record<string, number>; }
export interface ImportedSkill { id: string; name: string; tier: "Free" | "Premium"; desc: string; prompt: string; imported: true; }
export interface Settings { dest: string; years: number; everything: boolean; categories: string[]; openWhenDone: boolean; beta: boolean; }
export interface CategoryDef { key: string; label: string; sublabel: string; }
