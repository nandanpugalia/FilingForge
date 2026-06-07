// @vitest-environment jsdom
import { it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SkillsOverlay } from "../components/SkillsOverlay";
import * as api from "../api";
import * as ext from "../lib/openExternal";

// Node 26's native localStorage needs --localstorage-file; polyfill with the same in-memory
// shim the other unit tests use so the resume/pending logic works in all environments.
if (typeof globalThis.localStorage === "undefined" || globalThis.localStorage === null) {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      get length() { return store.size; },
      clear: () => store.clear(),
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      key: (i: number) => Array.from(store.keys())[i] ?? null,
      removeItem: (k: string) => { store.delete(k); },
      setItem: (k: string, v: string) => { store.set(k, String(v)); },
    } as Storage,
    configurable: true,
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  vi.spyOn(api, "getLibrary").mockResolvedValue([]);
});
afterEach(() => { localStorage.clear(); });

const owned = { id: "concall-decoder", name: "Concall Decoder", tier: "Premium" as const, desc: "decode", prompt: "DECODE BODY", imported: true as const };

it("(a) shows 'Get — ₹3,000' when not owned; clicking it runs checkout then opens the URL", async () => {
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  const checkout = vi.spyOn(api, "startCheckout").mockResolvedValue({ url: "https://rzp.io/i/abc", session: "sess-1" });
  const open = vi.spyOn(ext, "openExternal").mockResolvedValue();
  vi.spyOn(api, "redeem").mockResolvedValue({ status: "pending" });

  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  // Get is gated on a valid email — enter one first.
  await userEvent.type(await screen.findByLabelText(/Email for receipt/i), "buyer@example.com");
  const get = await screen.findByRole("button", { name: /Get — ₹3,000/ });
  await userEvent.click(get);

  await waitFor(() => expect(checkout).toHaveBeenCalledTimes(1));
  expect(checkout).toHaveBeenCalledWith("buyer@example.com");   // email carried to the worker
  expect(open).toHaveBeenCalledWith("https://rzp.io/i/abc");
  // session persisted for resume
  expect(localStorage.getItem("ff_pending_concall")).toBe("sess-1");
});

it("(a2) Get stays disabled until a valid email is entered", async () => {
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  const get = await screen.findByRole("button", { name: /Get — ₹3,000/ });
  expect(get).toBeDisabled();
  await userEvent.type(await screen.findByLabelText(/Email for receipt/i), "not-an-email");
  expect(get).toBeDisabled();
  await userEvent.clear(await screen.findByLabelText(/Email for receipt/i));
  await userEvent.type(await screen.findByLabelText(/Email for receipt/i), "ok@buyer.com");
  expect(get).toBeEnabled();
});

it("(b) a redeem returning md installs the pack and it shows as owned ('Use')", async () => {
  // first list empty (teaser shows Get), after install it's owned → "Use"
  vi.spyOn(api, "getSkills")
    .mockResolvedValueOnce([])
    .mockResolvedValue([owned]);
  vi.spyOn(api, "startCheckout").mockResolvedValue({ url: "https://rzp.io/i/x", session: "sess-2" });
  vi.spyOn(ext, "openExternal").mockResolvedValue();
  vi.spyOn(api, "redeem").mockResolvedValue({ status: "ready", md: "# CONCALL MD" });
  const install = vi.spyOn(api, "installSkillMd").mockResolvedValue(owned);

  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  await userEvent.type(await screen.findByLabelText(/Email for receipt/i), "buyer@example.com");
  await userEvent.click(await screen.findByRole("button", { name: /Get — ₹3,000/ }));

  // poll fires immediately? No — poll is interval-based. Use the "I've paid" button which appears once polling.
  const checkNow = await screen.findByRole("button", { name: /I've paid — check now/i });
  await userEvent.click(checkNow);

  await waitFor(() => expect(install).toHaveBeenCalledWith("Concall Decoder", "# CONCALL MD"));
  // owned now → a "Use" button exists for Concall Decoder and NO "Get" button
  expect(await screen.findByText(/Concall Decoder added ✓/)).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByRole("button", { name: /Get — ₹3,000/ })).not.toBeInTheDocument());
  expect(screen.getAllByRole("button", { name: /^Use$/ }).length).toBeGreaterThanOrEqual(1);
});

it("(c) paste-code path: pasting a session redeems and installs", async () => {
  vi.spyOn(api, "getSkills").mockResolvedValueOnce([]).mockResolvedValue([owned]);
  const redeem = vi.spyOn(api, "redeem").mockResolvedValue({ status: "ready", md: "# MD FROM CODE" });
  const install = vi.spyOn(api, "installSkillMd").mockResolvedValue(owned);

  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  const input = await screen.findByLabelText(/Redeem code/i);
  await userEvent.type(input, "pasted-session-uuid");
  await userEvent.click(screen.getByRole("button", { name: /^Redeem$/ }));

  await waitFor(() => expect(redeem).toHaveBeenCalledWith("pasted-session-uuid"));
  await waitFor(() => expect(install).toHaveBeenCalledWith("Concall Decoder", "# MD FROM CODE"));
});

it("(d) when concall-decoder is already imported, it shows 'Use' and NOT a duplicate 'Get' row", async () => {
  vi.spyOn(api, "getSkills").mockResolvedValue([owned]);
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  await waitFor(() => expect(screen.getAllByRole("button", { name: /^Use$/ }).length).toBeGreaterThanOrEqual(1));
  expect(await screen.findByText("Concall Decoder")).toBeInTheDocument();
  // owned → no buy teaser, no duplicate Concall Decoder name
  expect(screen.queryByRole("button", { name: /Get — ₹3,000/ })).not.toBeInTheDocument();
  expect(screen.getAllByText("Concall Decoder").length).toBe(1);
  expect(screen.getAllByRole("button", { name: /^Use$/ }).length).toBeGreaterThanOrEqual(1);
});

it("resume banner appears when a pending session exists and the pack isn't owned", async () => {
  localStorage.setItem("ff_pending_concall", "sess-resume");
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  expect(await screen.findByText(/Finish your Concall Decoder purchase/i)).toBeInTheDocument();
});

it("'Continue' reopens the saved payment URL (not a dead button)", async () => {
  localStorage.setItem("ff_pending_concall", "sess-resume");
  localStorage.setItem("ff_pending_concall_url", "https://rzp.io/i/resume");
  vi.spyOn(api, "getSkills").mockResolvedValue([]);
  vi.spyOn(api, "redeem").mockResolvedValue({ status: "pending" });
  const open = vi.spyOn(ext, "openExternal").mockResolvedValue();
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  await userEvent.click(await screen.findByRole("button", { name: /^Continue$/ }));
  await waitFor(() => expect(open).toHaveBeenCalledWith("https://rzp.io/i/resume"));
});

it("no resume banner once the pack is owned (and pending is cleared)", async () => {
  localStorage.setItem("ff_pending_concall", "sess-resume");
  vi.spyOn(api, "getSkills").mockResolvedValue([owned]);
  render(<SkillsOverlay root="/root" onClose={() => {}} />);
  await waitFor(() => expect(screen.getAllByRole("button", { name: /^Use$/ }).length).toBeGreaterThanOrEqual(1));
  await waitFor(() => expect(screen.queryByText(/Finish your Concall Decoder purchase/i)).not.toBeInTheDocument());
  await waitFor(() => expect(localStorage.getItem("ff_pending_concall")).toBeNull());
});
