import { it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchField } from "../components/SearchField";
import * as api from "../api";

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

const cands = [
  { scrip_code: "532790", company: "Tanla Platforms Ltd", is_primary: true, isin: "INE483C01032", symbol: "TANLA" },
  { scrip_code: "500325", company: "Reliance Industries Ltd", is_primary: false, isin: "INE002A01018", symbol: "RELIANCE" },
];

it("debounces, queries resolve, shows a dropdown, and picks by click", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue(cands);
  const onPick = vi.fn();
  render(<SearchField onPick={onPick} />);
  await userEvent.type(screen.getByPlaceholderText(/name or BSE code/i), "tan");
  await waitFor(() => expect(api.resolve).toHaveBeenCalledWith("tan"));
  await userEvent.click(await screen.findByText(/Tanla Platforms Ltd/));
  expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ scrip_code: "532790" }));
});

it("keyboard: ArrowDown then Enter picks the highlighted row", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue(cands);
  const onPick = vi.fn();
  render(<SearchField onPick={onPick} />);
  const input = screen.getByPlaceholderText(/name or BSE code/i);
  await userEvent.type(input, "rel");
  await screen.findByText(/Reliance Industries Ltd/);
  await userEvent.keyboard("{ArrowDown}{ArrowDown}{Enter}");   // move to 2nd row, select
  expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ scrip_code: "500325" }));
});

it("Escape clears the dropdown", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue(cands);
  render(<SearchField onPick={() => {}} />);
  const input = screen.getByPlaceholderText(/name or BSE code/i);
  await userEvent.type(input, "tan");
  await screen.findByText(/Tanla Platforms Ltd/);
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByText(/Tanla Platforms Ltd/)).not.toBeInTheDocument());
});

it("shows 'no company found' on empty results", async () => {
  vi.spyOn(api, "resolve").mockResolvedValue([]);
  render(<SearchField onPick={() => {}} />);
  await userEvent.type(screen.getByPlaceholderText(/name or BSE code/i), "zzzqq");
  expect(await screen.findByText(/no company found/i)).toBeInTheDocument();
});

it("shows the friendly error when resolve fails", async () => {
  vi.spyOn(api, "resolve").mockRejectedValue(new Error("BSE isn't responding right now."));
  render(<SearchField onPick={() => {}} />);
  await userEvent.type(screen.getByPlaceholderText(/name or BSE code/i), "tan");
  expect(await screen.findByText(/BSE isn't responding/)).toBeInTheDocument();
});
