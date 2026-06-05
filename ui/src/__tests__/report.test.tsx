import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportOverlay } from "../components/ReportOverlay";

beforeEach(() => vi.restoreAllMocks());

it("renders the form, gates Submit on Comment, and shows a graceful thanks with no worker URL", async () => {
  // BUG_WORKER_URL is empty in tests (no VITE_BUG_WORKER_URL) → no network call.
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  render(<ReportOverlay screen="search" onClose={() => {}} />);

  // type toggle present (default Bug pressed)
  expect(screen.getByRole("button", { name: /Bug/i })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: /Feature/i })).toBeInTheDocument();

  // auto-captured context shown
  expect(screen.getByText(/screen · search/i)).toBeInTheDocument();
  expect(screen.getByText(/version · 0\.1\.0/i)).toBeInTheDocument();

  // Submit disabled until Comment is non-empty
  const submit = screen.getByRole("button", { name: /^Send$/i });
  expect(submit).toBeDisabled();
  await userEvent.type(screen.getByRole("textbox", { name: /What went wrong/i }), "It crashed");
  expect(submit).toBeEnabled();

  // submitting with empty worker URL → friendly thanks, no fetch
  await userEvent.click(submit);
  expect(await screen.findByText(/feedback channel goes live at launch/i)).toBeInTheDocument();
  expect(fetchSpy).not.toHaveBeenCalled();
});
