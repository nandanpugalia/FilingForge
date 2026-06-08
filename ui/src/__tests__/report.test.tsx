import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Feedback POSTs to the Worker (which files the GitHub issue server-side, so the user needs
// no GitHub account). The browser-opened GitHub issue is only a FALLBACK when the Worker fails.
vi.mock("../lib/openExternal", () => ({ openExternal: vi.fn().mockResolvedValue(undefined) }));
import { ReportOverlay } from "../components/ReportOverlay";
import { openExternal } from "../lib/openExternal";
import { APP_VERSION, WORKER_URL } from "../config";

// Derived from the single source of truth so a version bump never breaks this test.
const VERSION_RE = new RegExp(`version · ${APP_VERSION.replace(/\./g, "\\.")}`, "i");

beforeEach(() => vi.clearAllMocks());

it("renders the form, gates Send on Comment, and POSTs the report to the Worker", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
  vi.stubGlobal("fetch", fetchMock);
  render(<ReportOverlay screen="search" onClose={() => {}} />);

  // type toggle present (default Bug pressed)
  expect(screen.getByRole("button", { name: /Bug/i })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: /Feature/i })).toBeInTheDocument();
  // auto-captured context shown
  expect(screen.getByText(/screen · search/i)).toBeInTheDocument();
  expect(screen.getByText(VERSION_RE)).toBeInTheDocument();

  // Send disabled until Comment is non-empty
  const submit = screen.getByRole("button", { name: /^Send$/i });
  expect(submit).toBeDisabled();
  await userEvent.type(screen.getByRole("textbox", { name: /What went wrong/i }), "It crashed on search");
  expect(submit).toBeEnabled();

  // submitting POSTs to the Worker /report with the comment + captured context
  await userEvent.click(submit);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [calledUrl, opts] = fetchMock.mock.calls[0];
  expect(calledUrl).toBe(`${WORKER_URL}/report`);
  const sent = JSON.parse((opts as { body: string }).body);
  expect(sent.comment).toBe("It crashed on search");
  expect(sent.version).toBe(APP_VERSION);
  expect(sent.screen).toBe("search");
  expect(openExternal).not.toHaveBeenCalled(); // Worker succeeded → no browser fallback
  expect(await screen.findByText(/your report's been sent/i)).toBeInTheDocument();
});

it("falls back to a prefilled GitHub issue if the Worker is unreachable", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<ReportOverlay screen="library" onClose={() => {}} />);
  await userEvent.type(screen.getByRole("textbox", { name: /What went wrong/i }), "network down");
  await userEvent.click(screen.getByRole("button", { name: /^Send$/i }));

  expect(openExternal).toHaveBeenCalledTimes(1);
  const url = (openExternal as unknown as { mock: { calls: string[][] } }).mock.calls[0][0];
  expect(url).toContain("github.com/nandanpugalia/FilingForge/issues/new");
  expect(decodeURIComponent(url)).toContain("network down");
  expect(await screen.findByText(/your report's been sent/i)).toBeInTheDocument();
});
