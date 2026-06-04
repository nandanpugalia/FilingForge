import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SettingsOverlay } from "../components/SettingsOverlay";
import { LibraryOverlay } from "../components/LibraryOverlay";
import { DEFAULT_SETTINGS } from "../settings";
import * as api from "../api";

beforeEach(() => vi.restoreAllMocks());

it("SettingsOverlay shows the donate options + a UPI image + closes", async () => {
  const onClose = vi.fn();
  render(<SettingsOverlay settings={DEFAULT_SETTINGS} onSave={() => {}} onClose={onClose} />);
  expect(screen.getByText(/GitHub Sponsors/i)).toBeInTheDocument();
  expect(screen.getByText(/Buy Me a Coffee/i)).toBeInTheDocument();
  expect(screen.getByAltText(/UPI/i)).toBeInTheDocument();              // static image, not text grid
  await userEvent.click(screen.getByRole("button", { name: /close/i })); expect(onClose).toHaveBeenCalled();
});

it("LibraryOverlay lists companies from the API (ticker + total only)", async () => {
  vi.spyOn(api, "getLibrary").mockResolvedValue([{ ticker: "TANLA", total: 42, counts: { "annual-reports": 1 } }]);
  render(<LibraryOverlay root="/root" onOpen={() => {}} onClose={() => {}} />);
  expect(await screen.findByText(/TANLA/)).toBeInTheDocument();
  expect(screen.getByText(/42/)).toBeInTheDocument();
});
