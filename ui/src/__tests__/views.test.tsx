import { it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProgressView } from "../components/ProgressView";
import { DoneView } from "../components/DoneView";
import { ErrorView } from "../components/ErrorView";
import type { PendingDocument } from "../types";

const pending: PendingDocument = {
  news_id: "news-1", date: "2026-07-28", headline: "Annual Report FY 2025-26",
  folder: "annual-reports", category: "Annual Reports", expected_type: "Annual report",
  expected_period: "FY 2025-26", bse_url: "https://www.bseindia.com/notice.pdf",
  issuer_url: "https://investor.kfintech.com/annual-reports/", reason: "The issuer page was ambiguous.",
};

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
  render(<DoneView ticker="TANLA" result={{ downloaded: 9, skipped: 1, failed: 0, pending: [] }} onOpen={onOpen} onReset={onReset} />);
  expect(screen.getByText(/9 documents added/)).toBeInTheDocument();
  expect(screen.getByText(/had no attached PDF/)).toBeInTheDocument();
  expect(screen.getByText(/An INDEX.md sits in the folder/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Open folder/i })); expect(onOpen).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /back to home/i })); expect(onReset).toHaveBeenCalled();
});

it("DoneView renders the category breakdown (mapped labels, sorted, zero-filtered)", () => {
  render(<DoneView ticker="TANLA" result={{ downloaded: 229, skipped: 0, failed: 0, pending: [] }}
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
    result={{ downloaded: 9, skipped: 0, failed: 0, pending: [] }} onOpen={() => {}} onReset={() => {}} />);
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
  render(<DoneView ticker="TANLA" result={{ downloaded: 9, skipped: 0, failed: 0, pending: [] }} onOpen={() => {}} onReset={() => {}} />);
  expect(screen.getByText(/9 documents added/)).toBeInTheDocument();
  expect(screen.queryByText(/By type/i)).not.toBeInTheDocument();
});

it("DoneView makes pending source PDFs explicit and actionable", async () => {
  const onOpenSource = vi.fn(), onUsePdf = vi.fn();
  render(<DoneView ticker="KFINTECH" name="KFin Technologies" dest="/lib"
    result={{ downloaded: 12, skipped: 0, failed: 0, pending: [pending] }}
    onOpen={() => {}} onReset={() => {}} onOpenPendingSource={onOpenSource}
    onUsePendingPdf={onUsePdf} importingPendingId={null} pendingErrors={{}} />);

  expect(screen.getByText(/12 documents ready · 1 awaiting source PDF/i)).toBeInTheDocument();
  expect(screen.getByText("Annual report")).toBeInTheDocument();
  expect(screen.getByText("FY 2025-26")).toBeInTheDocument();
  expect(screen.getByText(/investor\.kfintech\.com/)).toBeInTheDocument();
  expect(screen.getByText(/place it in the right folder, convert it to Markdown, and update the index/i)).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /Get document/i }));
  expect(onOpenSource).toHaveBeenCalledWith(pending);
  await userEvent.click(screen.getByRole("button", { name: /Use downloaded PDF/i }));
  expect(onUsePdf).toHaveBeenCalledWith(pending);
});

it("DoneView reports total ready documents rather than only this refresh's additions", () => {
  render(<DoneView ticker="KFINTECH"
    result={{ downloaded: 1, ready: 12, skipped: 0, failed: 0, pending: [pending] }}
    onOpen={() => {}} onReset={() => {}} />);

  expect(screen.getByText(/12 documents ready · 1 awaiting source PDF/i)).toBeInTheDocument();
  expect(screen.queryByText(/1 document ready ·/i)).not.toBeInTheDocument();
});

it("DoneView uses the BSE notice fallback and keeps an import error inline", () => {
  const noticeOnly = { ...pending, issuer_url: null };
  render(<DoneView ticker="KFINTECH" result={{ downloaded: 0, skipped: 0, failed: 0, pending: [noticeOnly] }}
    onOpen={() => {}} onReset={() => {}} onOpenPendingSource={() => {}}
    onUsePendingPdf={() => {}} importingPendingId={null}
    pendingErrors={{ "news-1": "That is another cover letter." }} />);

  expect(screen.getByRole("button", { name: /View BSE notice/i })).toBeInTheDocument();
  expect(screen.getByText("That is another cover letter.")).toBeInTheDocument();
  expect(screen.queryByText(/library is ready/i)).not.toBeInTheDocument();
});

it("ErrorView shows the friendly message, retries, opens the report form, and Back when given", async () => {
  const onRetry = vi.fn(), onReport = vi.fn(), onBack = vi.fn();
  render(<ErrorView message="BSE isn't responding right now." onRetry={onRetry} onReport={onReport} onBack={onBack} />);
  expect(screen.getByText(/BSE isn't responding/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Retry/i })); expect(onRetry).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /Report a problem/i })); expect(onReport).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /Back/i })); expect(onBack).toHaveBeenCalled();
});
