import { isTauri } from "../components/ReadyGate";

/**
 * Open an external URL in the user's real system browser.
 *
 * In a Tauri webview `<a target="_blank">` / `window.open` do NOT spawn the OS
 * browser, so external links silently do nothing. Inside Tauri we therefore use
 * the shell plugin's `open` (requires the `shell:allow-open` capability). In a
 * plain web build (or tests) we fall back to `window.open`.
 */
export async function openExternal(url: string): Promise<void> {
  if (isTauri()) {
    try {
      const { open } = await import("@tauri-apps/plugin-shell");
      await open(url);
      return;
    } catch {
      /* fall through to window.open if the plugin is unavailable */
    }
  }
  window.open(url, "_blank", "noopener,noreferrer");
}
