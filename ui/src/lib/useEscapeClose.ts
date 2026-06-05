import { useEffect } from "react";

/**
 * Closes an overlay when the user presses Escape.
 * Shared across all four overlays so the close behaviour is consistent
 * (✕ button + backdrop click + Escape key all call the same onClose).
 */
export function useEscapeClose(onClose: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
}
