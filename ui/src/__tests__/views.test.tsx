import { it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProgressView } from "../components/ProgressView";
import { DoneView } from "../components/DoneView";
import { ErrorView } from "../components/ErrorView";

it("ProgressView shows current item, percent, count, log feed, a11y, and a Back affordance", async () => {
  const onBack = vi.fn();
  render(<ProgressView progress={{ stage: "download", current: 6, total: 12, message: "Annual Report 2024", percent: 50 }}
    log={["AR 2025", "Q4 Results", "Annual Report 2024"]} onBack={onBack} />);
  expect(screen.getByText(/Annual Report 2024/)).toBeInTheDocument();
  expect(screen.getByText(/50%/)).toBeInTheDocument();
  expect(screen.getByText(/6 of 12/)).toBeInTheDocument();
  expect(screen.getByText(/Q4 Results/)).toBeInTheDocument();        // log feed renders
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  // smarter stage copy (not the raw "download") + a milestone marker at the % mark
  expect(screen.getByText(/Gathering filings/i)).toBeInTheDocument();
  expect(screen.getByText(/over halfway/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Back/i })); expect(onBack).toHaveBeenCalled();
});

it("ProgressView maps stage + percent to friendly copy and milestone words", () => {
  const { rerender } = render(<ProgressView
    progress={{ stage: "convert", current: 1, total: 4, message: "x", percent: 10 }} log={[]} onBack={() => {}} />);
  expect(screen.getByText(/Converting to clean Markdown/i)).toBeInTheDocument();
  expect(screen.getByText(/getting going/i)).toBeInTheDocument();
  rerender(<ProgressView progress={{ stage: "index", current: 4, total: 4, message: "x", percent: 100 }} log={[]} onBack={() => {}} />);
  expect(screen.getByText(/Building your index/i)).toBeInTheDocument();
  expect(screen.getByText(/^Done$/i)).toBeInTheDocument();
});

it("DoneView shows counts, skip note, AI hook, open + reset", async () => {
  const onOpen = vi.fn(), onReset = vi.fn();
  render(<DoneView ticker="TANLA" result={{ downloaded: 9, skipped: 1, failed: 0 }} onOpen={onOpen} onReset={onReset} />);
  expect(screen.getByText(/9 documents added/)).toBeInTheDocument();
  expect(screen.getByText(/had no attached PDF/)).toBeInTheDocument();
  expect(screen.getByText(/An INDEX.md sits in the folder/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Open folder/i })); expect(onOpen).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /back to home/i })); expect(onReset).toHaveBeenCalled();
});

it("DoneView renders the category breakdown (mapped labels, sorted, zero-filtered)", () => {
  render(<DoneView ticker="TANLA" result={{ downloaded: 229, skipped: 0, failed: 0 }}
    breakdown={{ "company-update": 188, "agm-egm": 13, "board-meeting": 11, "quarterly": 6, "press": 0, "weird-slug": 2 }}
    onOpen={() => {}} onReset={() => {}} />);
  expect(screen.getByText(/By type/i)).toBeInTheDocument();
  expect(screen.getByText("Company updates")).toBeInTheDocument();   // slug → nice label
  expect(screen.getByText("188")).toBeInTheDocument();
  expect(screen.getByText("AGM / EGM")).toBeInTheDocument();
  expect(screen.getByText("Financial results")).toBeInTheDocument(); // quarterly → Financial results
  expect(screen.getByText("Weird slug")).toBeInTheDocument();         // unknown slug titleized
  expect(screen.queryByText("Press releases")).not.toBeInTheDocument(); // zero count filtered out
});

it("DoneView renders a copyable AI prompt block with company + INDEX paths, Copy writes to clipboard", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  const { container } = render(<DoneView ticker="TANLA" name="Tanla Platforms Ltd" dest="/Users/np/Filings"
    result={{ downloaded: 9, skipped: 0, failed: 0 }} onOpen={() => {}} onReset={() => {}} />);
  // block is labelled and its body contains the company + both index paths
  expect(screen.getByText(/Paste this to your AI/i)).toBeInTheDocument();
  const body = container.querySelector(".ai-prompt-body")!;
  expect(body.textContent).toContain("Tanla Platforms Ltd");
  expect(body.textContent).toContain("/Users/np/Filings/TANLA/INDEX.md");
  expect(body.textContent).toContain("/Users/np/Filings/INDEX.md");
  // Copy button copies the full prompt text and flips to "Copied ✓"
  const copyBtn = screen.getByRole("button", { name: /^Copy$/i });
  await userEvent.click(copyBtn);
  expect(writeText).toHaveBeenCalledTimes(1);
  const arg = writeText.mock.calls[0][0] as string;
  expect(arg).toContain("Tanla Platforms Ltd");
  expect(arg).toContain("/Users/np/Filings/TANLA/INDEX.md");
  expect(arg).toContain("/Users/np/Filings/INDEX.md");
  expect(await screen.findByRole("button", { name: /Copied/i })).toBeInTheDocument();
});

it("DoneView renders gracefully with no breakdown (just the summary)", () => {
  render(<DoneView ticker="TANLA" result={{ downloaded: 9, skipped: 0, failed: 0 }} onOpen={() => {}} onReset={() => {}} />);
  expect(screen.getByText(/9 documents added/)).toBeInTheDocument();
  expect(screen.queryByText(/By type/i)).not.toBeInTheDocument();
});

it("ErrorView shows the friendly message, retries, opens the report form, and Back when given", async () => {
  const onRetry = vi.fn(), onReport = vi.fn(), onBack = vi.fn();
  render(<ErrorView message="BSE isn't responding right now." onRetry={onRetry} onReport={onReport} onBack={onBack} />);
  expect(screen.getByText(/BSE isn't responding/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Retry/i })); expect(onRetry).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /Report a problem/i })); expect(onReport).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /Back/i })); expect(onBack).toHaveBeenCalled();
});
