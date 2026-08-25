import { afterEach, beforeEach, expect, it, vi } from "vitest";

beforeEach(() => { vi.resetModules(); });
afterEach(() => {
  vi.doUnmock("../lib/isTauri");
  vi.doUnmock("@tauri-apps/api/path");
  vi.doUnmock("@tauri-apps/plugin-dialog");
  vi.resetModules();
});

it("returns null outside the desktop app without opening a dialog", async () => {
  const open = vi.fn();
  vi.doMock("../lib/isTauri", () => ({ isTauri: () => false }));
  vi.doMock("@tauri-apps/plugin-dialog", () => ({ open }));

  const { pickPdfFile } = await import("../lib/pickPdfFile");

  await expect(pickPdfFile()).resolves.toBeNull();
  expect(open).not.toHaveBeenCalled();
});

it("opens a single-PDF picker in Downloads and returns the chosen path", async () => {
  const open = vi.fn().mockResolvedValue("/Users/np/Downloads/report.pdf");
  vi.doMock("../lib/isTauri", () => ({ isTauri: () => true }));
  vi.doMock("@tauri-apps/api/path", () => ({ downloadDir: vi.fn().mockResolvedValue("/Users/np/Downloads") }));
  vi.doMock("@tauri-apps/plugin-dialog", () => ({ open }));

  const { pickPdfFile } = await import("../lib/pickPdfFile");
  const selected = await pickPdfFile();

  expect(selected).toBe("/Users/np/Downloads/report.pdf");
  expect(open).toHaveBeenCalledWith({
    directory: false,
    multiple: false,
    defaultPath: "/Users/np/Downloads",
    filters: [{ name: "PDF document", extensions: ["pdf"] }],
    title: "Choose the document PDF you downloaded",
  });
});

it("still opens the picker when the Downloads directory cannot be resolved", async () => {
  const open = vi.fn().mockResolvedValue(null);
  vi.doMock("../lib/isTauri", () => ({ isTauri: () => true }));
  vi.doMock("@tauri-apps/api/path", () => ({ downloadDir: vi.fn().mockRejectedValue(new Error("unavailable")) }));
  vi.doMock("@tauri-apps/plugin-dialog", () => ({ open }));

  const { pickPdfFile } = await import("../lib/pickPdfFile");
  await expect(pickPdfFile()).resolves.toBeNull();

  expect(open).toHaveBeenCalledWith(expect.not.objectContaining({ defaultPath: expect.anything() }));
});

it("surfaces a native dialog failure instead of treating it as cancellation", async () => {
  vi.doMock("../lib/isTauri", () => ({ isTauri: () => true }));
  vi.doMock("@tauri-apps/api/path", () => ({ downloadDir: vi.fn().mockResolvedValue("/Downloads") }));
  vi.doMock("@tauri-apps/plugin-dialog", () => ({
    open: vi.fn().mockRejectedValue(new Error("native dialog unavailable")),
  }));

  const { pickPdfFile } = await import("../lib/pickPdfFile");

  await expect(pickPdfFile()).rejects.toThrow(/couldn't open the PDF picker/i);
});
