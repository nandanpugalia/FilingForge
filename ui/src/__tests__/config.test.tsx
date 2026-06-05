import { it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfigPanel } from "../components/ConfigPanel";
import type { Candidate, Settings } from "../types";

const company: Candidate = { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, symbol: "TANLA" };
const settings: Settings = { dest: "~/FilingForgeLibrary", years: 1, everything: true, categories: ["annual_report","results","investor_ppt","concall"], openWhenDone: true };

function renderPanel(extra: Partial<React.ComponentProps<typeof ConfigPanel>> = {}) {
  const onBuild = vi.fn();
  render(<ConfigPanel company={company} settings={settings}
    starting={false} onChangeCompany={() => {}} onBuild={onBuild} {...extra} />);
  return { onBuild };
}

it("defaults from settings (all filings + years) and builds scope with symbol ticker + the global dest", async () => {
  const { onBuild } = renderPanel();
  expect(screen.getByLabelText(/All filings/i)).toBeChecked();
  await userEvent.click(screen.getByRole("button", { name: /Build library/i }));
  expect(onBuild).toHaveBeenCalledWith(expect.objectContaining({
    scrip_code: "532790", ticker: "TANLA", years: 1, everything: true, categories: [], dest: "~/FilingForgeLibrary" }));
});

it("toggling All filings off reveals 9 categories and sends keys", async () => {
  const { onBuild } = renderPanel();
  await userEvent.click(screen.getByLabelText(/All filings/i));   // OFF
  expect(screen.getByText(/Board-Meeting Outcomes/)).toBeInTheDocument();
  expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(9);
  await userEvent.click(screen.getByRole("button", { name: /Build library/i }));
  const scope = onBuild.mock.calls[0][0];
  expect(scope.everything).toBe(false);
  expect(scope.categories).toContain("annual_report");
});

it("Configure has NO destination override — the library folder is global (first run / Settings)", async () => {
  const onChangeCompany = vi.fn();
  render(<ConfigPanel company={company} settings={settings}
    starting={false} onChangeCompany={onChangeCompany} onBuild={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /change ✕|change company/i }));
  expect(onChangeCompany).toHaveBeenCalled();
  // no per-build destination input exists anymore
  expect(screen.queryByLabelText(/destination/i)).not.toBeInTheDocument();
});

it("disables the build button while starting (double-build guard)", () => {
  renderPanel({ starting: true });
  expect(screen.getByRole("button", { name: /Build library/i })).toBeDisabled();
});
