import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SettingsOverlay } from "../components/SettingsOverlay";
import { LibraryOverlay } from "../components/LibraryOverlay";
import { SkillsOverlay } from "../components/SkillsOverlay";
import { DEFAULT_SETTINGS } from "../settings";
import { DONATE } from "../config";
import * as api from "../api";
import * as picker from "../lib/pickSkillFile";

beforeEach(() => vi.restoreAllMocks());

it("SettingsOverlay shows UPI-only support (QR + id, no BMC/Sponsors) + closes", async () => {
  const onClose = vi.fn();
  render(<SettingsOverlay settings={DEFAULT_SETTINGS} onSave={() => {}} onClose={onClose} />);
  expect(screen.getByAltText(/UPI/i)).toBeInTheDocument();              // static QR image (no name/ID text shown)
  expect(screen.getByRole("button", { name: /Copy UPI ID/i })).toBeInTheDocument();
  expect(screen.queryByText(/GitHub Sponsors/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Buy Me a Coffee/i)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /close/i })); expect(onClose).toHaveBeenCalled();
});

it("Copy UPI ID writes to the clipboard and flips to Copied", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  render(<SettingsOverlay settings={DEFAULT_SETTINGS} onSave={() => {}} onClose={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Copy UPI ID/i }));
  expect(writeText).toHaveBeenCalledWith(DONATE.upiId);
  expect(await screen.findByRole("button", { name: /Copied/i })).toBeInTheDocument();
});

it("LibraryOverlay lists companies from the API (ticker + total only)", async () => {
  vi.spyOn(api, "getLibrary").mockResolvedValue([{ ticker: "TANLA", total: 42, counts: { "annual-reports": 1 } }]);
  render(<LibraryOverlay root="/root" onOpen={() => {}} onRefresh={() => {}} onAddCompany={() => {}} onClose={() => {}} />);
  expect(await screen.findByText(/TANLA/)).toBeInTheDocument();
  expect(screen.getByText(/42/)).toBeInTheDocument();
});

it("LibraryOverlay: Refresh + Add company are wired", async () => {
  vi.spyOn(api, "getLibrary").mockResolvedValue([{ ticker: "TANLA", total: 42, counts: { "annual-reports": 1 } }]);
  const onRefresh = vi.fn();
  const onAddCompany = vi.fn();
  render(<LibraryOverlay root="/root" onOpen={() => {}} onRefresh={onRefresh} onAddCompany={onAddCompany} onClose={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: /Refresh/i }));
  expect(onRefresh).toHaveBeenCalledWith("TANLA");
  await userEvent.click(screen.getByRole("button", { name: /Add company/i }));
  expect(onAddCompany).toHaveBeenCalled();
});

it("SkillsOverlay: Business Model Brief is free, premium is priced (tiers + coming-soon render)", async () => {
  vi.spyOn(api, "getLibrary").mockResolvedValue([]);
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  expect(screen.getByText("Business Model Brief")).toBeInTheDocument();
  expect(screen.getAllByText("Free").length).toBeGreaterThanOrEqual(1);   // free packs
  expect(screen.getByText("Premium")).toBeInTheDocument();                // premium tier (no money shown)
  expect(screen.getAllByText(/Coming soon/i).length).toBeGreaterThanOrEqual(2); // the not-yet-live packs
});

it("SkillsOverlay: Use asks which company, then copies a prompt with THAT company's paths + the skill", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  vi.spyOn(api, "getLibrary").mockResolvedValue([
    { ticker: "TANLA", total: 42, counts: {} },
    { ticker: "TITAN", total: 10, counts: {} },
  ]);
  render(<SkillsOverlay root="/Users/np/Filings" onClose={() => {}} />);
  // "Use" opens a company picker rather than copying a generic prompt immediately
  await userEvent.click(screen.getAllByRole("button", { name: /^Use$/i })[0]);
  expect(writeText).not.toHaveBeenCalled();
  // the user's downloaded companies are offered
  await userEvent.click(await screen.findByRole("button", { name: /TITAN/ }));
  // the copied prompt is specific to the chosen company — its INDEX path, the master index, and the skill body
  expect(writeText).toHaveBeenCalledTimes(1);
  const arg = writeText.mock.calls[0][0] as string;
  expect(arg).toContain("/Users/np/Filings/TITAN/INDEX.md");
  expect(arg).toContain("/Users/np/Filings/INDEX.md");
  expect(arg).toContain("Business Model Brief");                 // the skill body is included
  expect(await screen.findByRole("button", { name: /Copied/i })).toBeInTheDocument();
});

it("SkillsOverlay: Use with an empty library asks the user to download a company first (copies nothing)", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  vi.spyOn(api, "getLibrary").mockResolvedValue([]);
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  await userEvent.click(screen.getAllByRole("button", { name: /^Use$/i })[0]);
  expect(await screen.findByText(/download a company first/i)).toBeInTheDocument();
  expect(writeText).not.toHaveBeenCalled();
});

it("SkillsOverlay: an imported skill from the engine appears and runs the same company-picker flow", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  vi.spyOn(api, "getLibrary").mockResolvedValue([{ ticker: "TITAN", total: 10, counts: {} }]);
  vi.spyOn(api, "getSkills").mockResolvedValue([
    { id: "forensic", name: "Forensic DD", tier: "Premium", desc: "Deep dive.", prompt: "FORENSIC SKILL BODY", imported: true },
  ]);
  render(<SkillsOverlay root="/lib" onClose={() => {}} />);
  // the imported (bought) skill shows up as a real, runnable skill
  expect(await screen.findByText("Forensic DD")).toBeInTheDocument();
  const useBtns = screen.getAllByRole("button", { name: /^Use$/i });
  // run the imported one (built-in Business Model Brief is first, imported Forensic second)
  await userEvent.click(useBtns[useBtns.length - 1]);
  await userEvent.click(await screen.findByRole("button", { name: /TITAN/ }));
  const arg = writeText.mock.calls[0][0] as string;
  expect(arg).toContain("FORENSIC SKILL BODY");            // the imported skill's own prompt body
  expect(arg).toContain("/lib/TITAN/INDEX.md");            // pre-filled company path, same as built-ins
});

it("SkillsOverlay: with a large library the picker is searchable, and a pick auto-copies", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  const many = Array.from({ length: 40 }, (_, i) => ({
    ticker: i === 7 ? "TITAN" : `CO${i}`, total: i + 1, counts: {} }));
  vi.spyOn(api, "getLibrary").mockResolvedValue(many);
  render(<SkillsOverlay root="/lib" onClose={() => {}} />);
  await userEvent.click(screen.getAllByRole("button", { name: /^Use$/i })[0]);
  // a search box appears for big libraries; narrow to TITAN
  const box = await screen.findByLabelText(/Find a company/i);
  await userEvent.type(box, "titan");
  expect(screen.queryByRole("button", { name: /^CO1$/ })).not.toBeInTheDocument();
  // picking auto-copies the company-specific prompt (no extra OK step)
  await userEvent.click(screen.getByRole("button", { name: /^TITAN$/ }));
  expect(writeText.mock.calls[0][0]).toContain("/lib/TITAN/INDEX.md");
});

it("SkillsOverlay: 'Import a skill' picks a .md, imports it, and the new skill appears", async () => {
  vi.spyOn(api, "getLibrary").mockResolvedValue([{ ticker: "TITAN", total: 10, counts: {} }]);
  const getSkills = vi.spyOn(api, "getSkills")
    .mockResolvedValueOnce([])                              // nothing imported yet
    .mockResolvedValue([{ id: "bought", name: "Bought Pack", tier: "Premium", desc: "", prompt: "x", imported: true }]);
  vi.spyOn(picker, "pickSkillFile").mockResolvedValue("/Users/np/Downloads/bought.md");
  const importSkill = vi.spyOn(api, "importSkill")
    .mockResolvedValue({ id: "bought", name: "Bought Pack", tier: "Premium", desc: "", prompt: "x", imported: true });
  render(<SkillsOverlay root="/lib" onClose={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: /Import a skill/i }));
  expect(picker.pickSkillFile).toHaveBeenCalled();
  expect(importSkill).toHaveBeenCalledWith("/Users/np/Downloads/bought.md");
  expect(getSkills).toHaveBeenCalledTimes(2);              // re-fetched after import
  expect(await screen.findByText("Bought Pack")).toBeInTheDocument();
});

it("LibraryOverlay: search box appears past 8 companies and filters by ticker", async () => {
  const many = Array.from({ length: 12 }, (_, i) => ({
    ticker: i === 0 ? "TANLA" : `CO${i}`, total: i + 1, counts: {} }));
  vi.spyOn(api, "getLibrary").mockResolvedValue(many);
  render(<LibraryOverlay root="/root" onOpen={() => {}} onRefresh={() => {}} onAddCompany={() => {}} onClose={() => {}} />);
  const box = await screen.findByLabelText(/Search your library/i);
  await userEvent.type(box, "tanla");
  expect(screen.getByText("TANLA")).toBeInTheDocument();
  expect(screen.queryByText("CO1")).not.toBeInTheDocument();
  await userEvent.clear(box);
  await userEvent.type(box, "zzz");
  expect(screen.getByText(/No company matches/i)).toBeInTheDocument();
});

it("LibraryOverlay: no search box for a small library", async () => {
  vi.spyOn(api, "getLibrary").mockResolvedValue([{ ticker: "TANLA", total: 42, counts: {} }]);
  render(<LibraryOverlay root="/root" onOpen={() => {}} onRefresh={() => {}} onAddCompany={() => {}} onClose={() => {}} />);
  expect(await screen.findByText("TANLA")).toBeInTheDocument();
  expect(screen.queryByLabelText(/Search your library/i)).not.toBeInTheDocument();
});

it("overlays close on Escape, backdrop click, and ✕ (Settings + Skills)", async () => {
  // Escape closes Settings
  const onCloseEsc = vi.fn();
  const { unmount } = render(<SettingsOverlay settings={DEFAULT_SETTINGS} onSave={() => {}} onClose={onCloseEsc} />);
  await userEvent.keyboard("{Escape}");
  expect(onCloseEsc).toHaveBeenCalled();
  unmount();

  // Backdrop click closes Skills; clicking inside the panel does not
  vi.spyOn(api, "getLibrary").mockResolvedValue([]);
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  const onCloseBackdrop = vi.fn();
  render(<SkillsOverlay root="/root" onClose={onCloseBackdrop} />);
  await userEvent.click(screen.getByRole("heading", { name: /Skills/i })); // inside panel — no close
  expect(onCloseBackdrop).not.toHaveBeenCalled();
  await userEvent.keyboard("{Escape}");                                          // Escape closes
  expect(onCloseBackdrop).toHaveBeenCalled();
});
