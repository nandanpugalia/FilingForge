import { useState } from "react";
import { APP_VERSION } from "../config";
import { useEscapeClose } from "../lib/useEscapeClose";
import { openExternal } from "../lib/openExternal";

const REPO = "nandanpugalia/FilingForge";

type ReportType = "bug" | "feature";
type Status = "idle" | "sending" | "sent" | "failed";

function detectOs(): string {
  const nav = typeof navigator !== "undefined" ? navigator : undefined;
  return nav?.platform || nav?.userAgent || "unknown";
}

export function ReportOverlay({ screen, onClose }: { screen: string; onClose: () => void }) {
  const [type, setType] = useState<ReportType>("bug");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  useEscapeClose(onClose);

  const os = detectOs();
  const canSubmit = comment.trim().length > 0 && status !== "sending";

  async function submit() {
    if (!canSubmit) return;
    setStatus("sending");

    // Open a prefilled GitHub issue in the system browser. Trackable, no backend,
    // and the repo's GitHub→Discord webhook notifies the maintainer automatically.
    const kind = type === "bug" ? "Bug" : "Feature";
    const label = type === "bug" ? "bug" : "enhancement";
    const title = `[${kind}] ${comment.trim().slice(0, 60)}`;
    const body = [
      comment.trim(),
      "",
      "---",
      `- **Type:** ${type}`,
      `- **App version:** ${APP_VERSION}`,
      `- **Screen:** ${screen}`,
      `- **System:** ${os}`,
      name ? `- **From:** ${name}` : "",
      email ? `- **Contact:** ${email}` : "",
    ].filter(Boolean).join("\n");
    const url =
      `https://github.com/${REPO}/issues/new` +
      `?labels=${encodeURIComponent(label)}` +
      `&title=${encodeURIComponent(title)}` +
      `&body=${encodeURIComponent(body)}`;

    try {
      await openExternal(url);
      setStatus("sent");
      setTimeout(onClose, 1800);
    } catch {
      setStatus("failed");
    }
  }

  const message =
    status === "sent" ? "Opening GitHub to post your report — thank you! 🙏" :
    status === "failed" ? "Couldn't open the browser — please try again." : null;

  return (
    <div className="overlay" role="dialog" aria-label="Send feedback" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-head">
          <h3>Tell us what's up</h3>
          <button className="close" aria-label="close" onClick={onClose}>✕</button>
        </div>

        <div className="report-type" role="group" aria-label="report type">
          <button type="button"
            className={`seg ${type === "bug" ? "on" : ""}`}
            aria-pressed={type === "bug"}
            onClick={() => setType("bug")}>🐞 Bug</button>
          <button type="button"
            className={`seg ${type === "feature" ? "on" : ""}`}
            aria-pressed={type === "feature"}
            onClick={() => setType("feature")}>💡 Feature</button>
        </div>

        <label>Name
          <input value={name} placeholder="optional" onChange={(e) => setName(e.target.value)} /></label>
        <label>Email
          <input value={email} placeholder="optional, for a reply" onChange={(e) => setEmail(e.target.value)} /></label>
        <label>{type === "bug" ? "What went wrong?" : "What would you like?"}
          <textarea className="report-comment" value={comment} rows={4}
            placeholder={type === "bug" ? "Tell us what happened…" : "Describe the idea…"}
            onChange={(e) => setComment(e.target.value)} /></label>

        <div className="report-context" aria-label="captured details">
          <span>screen · {screen}</span>
          <span>version · {APP_VERSION}</span>
          <span>system · {os}</span>
        </div>

        {message && <div className={`report-status ${status}`}>{message}</div>}

        <button className="primary" disabled={!canSubmit} onClick={submit}>
          {status === "sending" ? "Opening…" : "Send"}
        </button>
      </div>
    </div>
  );
}
