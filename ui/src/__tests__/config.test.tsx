import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfigPanel } from "../components/ConfigPanel";
import type { Candidate, Settings } from "../types";
import * as api from "../api";

// Build now PREVIEWS first (count + breakdown) then the user clicks Download → onBuild.
vi.mock("../api", () => ({
  previewBuild: vi.fn(async () => ({
    total: 5, new: 5, have: 0,
    by_category: [{ label: "Annual Reports", count: 2 }, { label: "Financial Results", count: 3 }],
  })),
}));

const company: Candidate = { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, symbol: "TANLA" };
const settings: Settings = { dest: "~/FilingForgeLibrary", years: 1, everything: true, categories: ["annual_report","results","investor_ppt","concall"], openWhenDone: true, beta: false };

beforeEach(() => { vi.mocked(api.previewBuild).mockClear(); });

function renderPanel(extra: Partial<React.ComponentProps<typeof ConfigPanel>> = {}) {
  const onBuild = vi.fn();
  render(<ConfigPanel company={company} settings={settings}
    starting={false} onChangeCompany={() => {}} onBuild={onBuild} {...extra} />);
  return { onBuild };
}

// click Build → wait for preview → click Download
async function buildThenDownload() {
  await userEvent.click(screen.getByRole("button", { name: /Build library/i }));
  const dl = await screen.findByRole("button", { name: /Download \d+/i });
  await userEvent.click(dl);
}

it("previews then builds scope with symbol ticker + the global dest (all filings)", async () => {
  const { onBuild } = renderPanel();
  expect(screen.getByLabelText(/All filings/i)).toBeChecked();
  await buildThenDownload();
  expect(api.previewBuild).toHaveBeenCalled();
  expect(onBuild).toHaveBeenCalledWith(expect.objectContaining({
    scrip_code: "532790", ticker: "TANLA", years: 1, everything: true, categories: [], dest: "~/FilingForgeLibrary" }));
});

it("toggling All filings off reveals 9 categories and sends keys", async () => {
  const { onBuild } = renderPanel();
  await userEvent.click(screen.getByLabelText(/All filings/i));   // OFF
  expect(screen.getByText(/Board-Meeting Outcomes/)).toBeInTheDocument();
  expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(9);
  await buildThenDownload();
  const scope = onBuild.mock.calls[0][0];
  expect(scope.everything).toBe(false);
  expect(scope.categories).toContain("annual_report");
});

it("the preview shows the per-category breakdown before downloading", async () => {
  renderPanel();
  await userEvent.click(screen.getByRole("button", { name: /Build library/i }));
  // count + label are separate spans; assert each + the breakdown rows
  expect(await screen.findByText(/new filing/i)).toBeInTheDocument();
  expect(screen.getByText("Annual Reports")).toBeInTheDocument();
  expect(screen.getByText("Financial Results")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Download 5/i })).toBeInTheDocument();
});

it("Configure has NO destination override — the library folder is global (first run / Settings)", async () => {
  const onChangeCompany = vi.fn();
  render(<ConfigPanel company={company} settings={settings}
    starting={false} onChangeCompany={onChangeCompany} onBuild={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /change ✕|change company/i }));
  expect(onChangeCompany).toHaveBeenCalled();
  expect(screen.queryByLabelText(/destination/i)).not.toBeInTheDocument();
});

it("disables the build button while starting (double-build guard)", () => {
  renderPanel({ starting: true });
  expect(screen.getByRole("button", { name: /Build library/i })).toBeDisabled();
});
