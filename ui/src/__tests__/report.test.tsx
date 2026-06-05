import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Feedback opens a prefilled GitHub issue in the system browser.
vi.mock("../lib/openExternal", () => ({ openExternal: vi.fn().mockResolvedValue(undefined) }));
import { ReportOverlay } from "../components/ReportOverlay";
import { openExternal } from "../lib/openExternal";
import { APP_VERSION } from "../config";

// Derived from the single source of truth so a version bump never breaks this test.
const VERSION_RE = new RegExp(`version · ${APP_VERSION.replace(/\./g, "\\.")}`, "i");

beforeEach(() => vi.clearAllMocks());

it("renders the form, gates Send on Comment, and files a prefilled GitHub issue on submit", async () => {
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

  // submitting opens a prefilled GitHub issue with the comment + captured context
  await userEvent.click(submit);
  expect(openExternal).toHaveBeenCalledTimes(1);
  const url = (openExternal as unknown as { mock: { calls: string[][] } }).mock.calls[0][0];
  expect(url).toContain("github.com/nandanpugalia/FilingForge/issues/new");
  const decoded = decodeURIComponent(url);
  expect(decoded).toContain("It crashed on search");
  expect(decoded).toContain(APP_VERSION); // app version captured in the issue body
  expect(await screen.findByText(/Opening GitHub/i)).toBeInTheDocument();
});
