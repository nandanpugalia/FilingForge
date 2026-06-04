import { it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProgressView } from "../components/ProgressView";
import { DoneView } from "../components/DoneView";
import { ErrorView } from "../components/ErrorView";

it("ProgressView shows current item, percent, count, and the log feed + a11y", () => {
  render(<ProgressView progress={{ stage: "download", current: 6, total: 12, message: "Annual Report 2024", percent: 50 }}
    log={["AR 2025", "Q4 Results", "Annual Report 2024"]} onCancel={() => {}} />);
  expect(screen.getByText(/Annual Report 2024/)).toBeInTheDocument();
  expect(screen.getByText(/50%/)).toBeInTheDocument();
  expect(screen.getByText(/6 of 12/)).toBeInTheDocument();
  expect(screen.getByText(/Q4 Results/)).toBeInTheDocument();        // log feed renders
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
});

it("DoneView shows counts, skip note, AI hook, open + reset", async () => {
  const onOpen = vi.fn(), onReset = vi.fn();
  render(<DoneView ticker="TANLA" result={{ downloaded: 9, skipped: 1, failed: 0 }} onOpen={onOpen} onReset={onReset} />);
  expect(screen.getByText(/9 documents added/)).toBeInTheDocument();
  expect(screen.getByText(/had no attached PDF/)).toBeInTheDocument();
  expect(screen.getByText(/INDEX.md/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Open folder/i })); expect(onOpen).toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: /build another/i })); expect(onReset).toHaveBeenCalled();
});

it("ErrorView shows the friendly message and retries", async () => {
  const onRetry = vi.fn();
  render(<ErrorView message="BSE isn't responding right now." onRetry={onRetry} />);
  expect(screen.getByText(/BSE isn't responding/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Retry/i })); expect(onRetry).toHaveBeenCalled();
});
