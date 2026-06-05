import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FirstRunOverlay } from "../components/FirstRunOverlay";

beforeEach(() => vi.restoreAllMocks());

it("FirstRunOverlay: asks one thing — where the library lives — and Continue returns the chosen folder", async () => {
  const onComplete = vi.fn();
  render(<FirstRunOverlay defaultDest="~/Documents/FilingForgeLibrary" onComplete={onComplete} />);
  expect(screen.getByRole("heading", { name: /set up your library/i })).toBeInTheDocument();
  const input = screen.getByLabelText(/library folder/i);
  await userEvent.clear(input);
  await userEvent.type(input, "/Users/me/Filings");
  await userEvent.click(screen.getByRole("button", { name: /continue|get started/i }));
  expect(onComplete).toHaveBeenCalledWith("/Users/me/Filings");
});

it("FirstRunOverlay: Continue with no edit uses the default folder", async () => {
  const onComplete = vi.fn();
  render(<FirstRunOverlay defaultDest="~/Documents/FilingForgeLibrary" onComplete={onComplete} />);
  await userEvent.click(screen.getByRole("button", { name: /continue|get started/i }));
  expect(onComplete).toHaveBeenCalledWith("~/Documents/FilingForgeLibrary");
});
