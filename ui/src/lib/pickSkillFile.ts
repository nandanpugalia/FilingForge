import { isTauri } from "./isTauri";

/**
 * Open the native OS file picker for a Skill's Markdown file (the .md a user
 * downloaded after buying a premium pack, or a community skill).
 *
 * Returns the selected absolute path, or `null` if the user cancelled or if we
 * are running in a plain web browser (no native picker). Mirrors pickFolder —
 * the dialog plugin is imported dynamically so web builds/tests never pull in
 * the Tauri runtime.
 */
export async function pickSkillFile(): Promise<string | null> {
  if (!isTauri()) return null;
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      directory: false,
      multiple: false,
      filters: [{ name: "Skill", extensions: ["md"] }],
      title: "Choose a skill (.md) to import",
    });
    if (typeof selected === "string") return selected;
    return null;
  } catch {
    return null;
  }
}
