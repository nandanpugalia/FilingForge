import { it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { WORKER_URL } from "../config";

function Boom(): never {
  throw new Error("kaboom");
}

beforeEach(() => {
  // React logs caught render errors to console.error — silence it for clean output.
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => vi.restoreAllMocks());

it("renders its children when nothing throws", () => {
  render(
    <ErrorBoundary>
      <p>all good</p>
    </ErrorBoundary>
  );
  expect(screen.getByText("all good")).toBeInTheDocument();
});

it("renders a recoverable fallback (message + Reload) when a child throws", () => {
  render(
    <ErrorBoundary>
      <Boom />
    </ErrorBoundary>
  );
  // The whole app must NOT white-screen: a themed message + a way out is shown.
  expect(screen.getByText(/something broke/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /reload/i })).toBeInTheDocument();
  // and a way to report it, since the in-app report button is gone after a crash
  expect(screen.getByRole("button", { name: /report this/i })).toBeInTheDocument();
});

it("reports a crash through the Worker (same flow as the in-app reporter)", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
  vi.stubGlobal("fetch", fetchMock);
  render(
    <ErrorBoundary>
      <Boom />
    </ErrorBoundary>
  );
  await userEvent.click(screen.getByRole("button", { name: /report this/i }));

  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url, opts] = fetchMock.mock.calls[0];
  expect(url).toBe(`${WORKER_URL}/report`);
  const sent = JSON.parse((opts as { body: string }).body);
  expect(sent.screen).toBe("crash");
  expect(sent.comment).toContain("kaboom");
  expect(await screen.findByText(/reported — thank you/i)).toBeInTheDocument();
});
