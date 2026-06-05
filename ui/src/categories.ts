import type { CategoryDef } from "./types";
// Keys MUST match engine/models.py CURATED_BY_KEY (underscore keys, NOT folder slugs).
export const CATEGORIES: CategoryDef[] = [
  { key: "annual_report", label: "Annual Reports", sublabel: "the yearly report & financials" },
  { key: "results", label: "Financial Results", sublabel: "quarterly numbers" },
  { key: "investor_ppt", label: "Investor Presentations", sublabel: "management's slide decks" },
  { key: "concall", label: "Concall Transcripts", sublabel: "earnings-call transcripts" },
  { key: "board_outcome", label: "Board-Meeting Outcomes", sublabel: "what the board decided" },
  { key: "press", label: "Press / Media Releases", sublabel: "official announcements" },
  { key: "analyst_meet", label: "Analyst / Investor Meets", sublabel: "meeting & roadshow notices" },
  { key: "corp_actions", label: "Dividends & Corp Actions", sublabel: "dividends, record dates, buybacks" },
  { key: "agm_egm", label: "AGM / EGM", sublabel: "shareholder-meeting documents" },
];
export const DEFAULT_CURATED = ["annual_report", "results", "investor_ppt", "concall"];
