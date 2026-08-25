/** True only inside the Tauri webview (the desktop app). */
export function isTauri(): boolean {
  return typeof window !== "undefined" &&
    typeof (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ !== "undefined";
}
