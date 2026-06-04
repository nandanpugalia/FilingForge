import { it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfigPanel } from "../components/ConfigPanel";
import type { Candidate, Settings } from "../types";

const company: Candidate = { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, symbol: "TANLA" };
const settings: Settings = { dest: "~/FilingForgeLibrary", years: 1, everything: true, categories: ["annual_report","results","investor_ppt","concall"], openWhenDone: true };

function renderPanel(extra: Partial<React.ComponentProps<typeof ConfigPanel>> = {}) {
  const onBuild = vi.fn();
  render(<ConfigPanel company={company} dest={settings.dest} settings={settings}
    starting={false} onChangeCompany={() => {}} onDestChange={() => {}} onBuild={onBuild} {...extra} />);
  return { onBuild };
}

it("defaults from settings (everything + years) and builds scope with symbol ticker", async () => {
  const { onBuild } = renderPanel();
  expect(screen.getByText(/Everything — all filings/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Get the filings/i }));
  expect(onBuild).toHaveBeenCalledWith(expect.objectContaining({
    scrip_code: "532790", ticker: "TANLA", years: 1, everything: true, categories: [] }));
});

it("toggling Everything off reveals 9 categories and sends keys", async () => {
  const { onBuild } = renderPanel();
  await userEvent.click(screen.getByLabelText(/Everything — all filings/i));   // OFF
  expect(screen.getByText(/Board-Meeting Outcomes/)).toBeInTheDocument();
  expect(screen.getAllByRole("checkbox").length).toBeGreaterThanOrEqual(9);    // 9 cats (+the everything box is now off)
  await userEvent.click(screen.getByRole("button", { name: /Get the filings/i }));
  const scope = onBuild.mock.calls[0][0];
  expect(scope.everything).toBe(false);
  expect(scope.categories).toContain("annual_report");
});

it("change-company and change-dest are SEPARATE actions", async () => {
  const onChangeCompany = vi.fn(); const onDestChange = vi.fn();
  render(<ConfigPanel company={company} dest={settings.dest} settings={settings}
    starting={false} onChangeCompany={onChangeCompany} onDestChange={onDestChange} onBuild={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /change ✕|change company/i }));
  expect(onChangeCompany).toHaveBeenCalled();
  expect(onDestChange).not.toHaveBeenCalled();
  await userEvent.type(screen.getByLabelText(/destination/i), "X");
  expect(onDestChange).toHaveBeenCalled();
});

it("disables the build button while starting (double-build guard)", () => {
  renderPanel({ starting: true });
  expect(screen.getByRole("button", { name: /Get the filings/i })).toBeDisabled();
});
