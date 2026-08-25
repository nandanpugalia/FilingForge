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

it("DoneView leads with the complete library outcome and both actions", async () => {
  const onOpen = vi.fn(), onReset = vi.fn();
  render(<DoneView ticker="KFINTECH" name="KFin Technologies Ltd"
    result={{ downloaded: 28, ready: 28, skipped: 0, failed: 0, pending: [] }}
    onOpen={onOpen} onReset={onReset} />);
  expect(screen.getByRole("heading", { name: "Library ready" })).toBeInTheDocument();
  expect(screen.getByText("KFin Technologies Ltd")).toBeInTheDocument();
  expect(screen.getByText(/28 official filings ready for your AI/i)).toBeInTheDocument();
  expect(screen.getByText(/28 added/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy AI instructions/i })).toHaveClass("primary");
  await userEvent.click(screen.getByRole("button", { name: /Open library/i })); expect(onOpen).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /back to home/i })); expect(onReset).toHaveBeenCalled();
});

it("DoneView describes refresh facts without calling already-present files missing", () => {
  render(<DoneView ticker="KFINTECH" name="KFin Technologies Ltd"
    result={{ downloaded: 2, ready: 28, skipped: 26, failed: 1, pending: [] }}
    onOpen={() => {}} onReset={() => {}} />);

  expect(screen.getByText(/28 official filings ready for your AI/i)).toBeInTheDocument();
  expect(screen.getByText(/2 new/i)).toBeInTheDocument();
  expect(screen.getByText(/26 already in your library/i)).toBeInTheDocument();
  expect(screen.getByText(/1 couldn't be added/i)).toBeInTheDocument();
  expect(screen.queryByText(/had no attached PDF/i)).not.toBeInTheDocument();
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

it("DoneView copies the approved company-index handoff only after a click", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  render(<DoneView ticker="TANLA" name="Tanla Platforms Ltd" dest="/Users/np/Filings"
    result={{ downloaded: 9, ready: 9, skipped: 0, failed: 0, pending: [] }} onOpen={() => {}} onReset={() => {}} />);
  expect(writeText).not.toHaveBeenCalled();
  expect(screen.queryByText(/\/Users\/np\/Filings/)).not.toBeInTheDocument();

  const copyBtn = screen.getByRole("button", { name: /Copy AI instructions/i });
  await userEvent.click(copyBtn);
  expect(writeText).toHaveBeenCalledTimes(1);
  const arg = writeText.mock.calls[0][0] as string;
  expect(arg).toBe(
    "I've built a local filings library for Tanla Platforms Ltd.\n" +
    "Read its index first: /Users/np/Filings/TANLA/INDEX.md\n" +
    "Use only the official filings in that library and cite the filenames you rely on.\n" +
    "Tell me when you've read the index and are ready, then wait for my question."
  );
  expect(arg).not.toContain("Other companies");
  expect(arg).not.toContain("/Users/np/Filings/INDEX.md");
  expect(await screen.findByRole("button", { name: /Copied/i })).toBeInTheDocument();
});

it("DoneView keeps clipboard failures visible and retryable", async () => {
  const writeText = vi.fn().mockRejectedValue(new Error("permission denied"));
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  render(<DoneView ticker="TANLA" dest="/lib"
    result={{ downloaded: 9, ready: 9, skipped: 0, failed: 0, pending: [] }}
    onOpen={() => {}} onReset={() => {}} />);

  await userEvent.click(screen.getByRole("button", { name: /Copy AI instructions/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't copy/i);
  expect(screen.getByRole("button", { name: /Copy AI instructions/i })).toBeEnabled();
});

it("DoneView renders gracefully with no breakdown (just the summary)", () => {
  render(<DoneView ticker="TANLA" result={{ downloaded: 9, ready: 9, skipped: 0, failed: 0, pending: [] }} onOpen={() => {}} onReset={() => {}} />);
  expect(screen.getByText(/9 official filings ready for your AI/i)).toBeInTheDocument();
  expect(screen.queryByText(/By type/i)).not.toBeInTheDocument();
});

it("DoneView makes pending source PDFs explicit and actionable", async () => {
  const onOpenSource = vi.fn(), onUsePdf = vi.fn();
  render(<DoneView ticker="KFINTECH" name="KFin Technologies" dest="/lib"
    result={{ downloaded: 12, skipped: 0, failed: 0, pending: [pending] }}
    onOpen={() => {}} onReset={() => {}} onOpenPendingSource={onOpenSource}
    onUsePendingPdf={onUsePdf} importingPendingId={null} pendingErrors={{}} />);

  expect(screen.getByRole("heading", { name: /Library almost ready/i })).toBeInTheDocument();
  expect(screen.getByText(/12 official filings ready/i)).toBeInTheDocument();
  expect(screen.getByText(/1 needs its source PDF/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Copy AI instructions/i })).not.toBeInTheDocument();
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

  expect(screen.getByText(/12 official filings ready/i)).toBeInTheDocument();
  expect(screen.queryByText(/1 official filing ready/i)).not.toBeInTheDocument();
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

it("DoneView describes a cancelled build as safely saved rather than fully completed", () => {
  render(<DoneView ticker="TANLA"
    result={{ downloaded: 2, ready: 7, skipped: 5, failed: 0, pending: [], cancelled: true }}
    onOpen={() => {}} onReset={() => {}} />);

  expect(screen.getByRole("heading", { name: /Saved safely/i })).toBeInTheDocument();
  expect(screen.getByText(/7 complete official filings are ready/i)).toBeInTheDocument();
});

it("ErrorView shows the friendly message, retries, opens the report form, and Back when given", async () => {
  const onRetry = vi.fn(), onReport = vi.fn(), onBack = vi.fn();
  render(<ErrorView message="BSE isn't responding right now." onRetry={onRetry} onReport={onReport} onBack={onBack} />);
  expect(screen.getByText(/BSE isn't responding/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Retry/i })); expect(onRetry).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /Report a problem/i })); expect(onReport).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /Back/i })); expect(onBack).toHaveBeenCalled();
});
