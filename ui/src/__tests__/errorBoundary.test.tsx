import { it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../components/ErrorBoundary";

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
