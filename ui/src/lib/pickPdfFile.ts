import { isTauri } from "../components/ReadyGate";

/** Pick one user-downloaded PDF without asking where it belongs in the library. */
export async function pickPdfFile(): Promise<string | null> {
  if (!isTauri()) return null;

  let defaultPath: string | undefined;
  try {
    const { downloadDir } = await import("@tauri-apps/api/path");
    defaultPath = await downloadDir();
  } catch {
    // The native dialog is still useful when the OS does not expose Downloads.
  }

  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      directory: false,
      multiple: false,
      ...(defaultPath ? { defaultPath } : {}),
      filters: [{ name: "PDF document", extensions: ["pdf"] }],
      title: "Choose the document PDF you downloaded",
    });
    return typeof selected === "string" ? selected : null;
  } catch {
    return null;
  }
}
