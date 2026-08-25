import { isTauri } from "./isTauri";

/**
 * Open the native OS directory picker when running inside the Tauri desktop app.
 *
 * Returns the selected absolute path, or `null` if the user cancelled or if we
 * are running in a plain web browser (where no native picker exists — callers
 * should keep the text field as the fallback).
 *
 * The dialog plugin is imported dynamically so a plain web build never pulls in
 * the Tauri runtime (and tests don't need it mocked).
 */
export async function pickFolder(defaultPath?: string): Promise<string | null> {
  if (!isTauri()) return null;
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      directory: true,
      multiple: false,
      defaultPath,
      title: "Choose where to save your FilingForge library",
    });
    if (typeof selected === "string") return selected;
    return null;
  } catch {
    return null;
  }
}
