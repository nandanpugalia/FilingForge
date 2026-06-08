import { useState } from "react";
import { APP_VERSION, WORKER_URL } from "../config";
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

  // Open a prefilled GitHub issue in the system browser — the FALLBACK path, used only if
  // the Worker submit fails. Needs a GitHub account, so it's no longer the primary route.
  async function openGithubFallback() {
    const kind = type === "bug" ? "Bug" : "Feature";
    const label = type === "bug" ? "bug" : "enhancement";
    const title = `[${kind}] ${comment.trim().slice(0, 60)}`;
    const body = [
      comment.trim(), "", "---",
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
    await openExternal(url);
  }

  async function submit() {
    if (!canSubmit) return;
    setStatus("sending");
    // PRIMARY path: send to the Worker, which files the GitHub issue server-side (so the user
    // needs NO GitHub account) and pings Discord. Email is sent for a reply, kept private.
    try {
      const res = await fetch(`${WORKER_URL}/report`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          type, comment: comment.trim(), name: name.trim(), email: email.trim(),
          version: APP_VERSION, screen, os,
        }),
      });
      if (!res.ok) throw new Error(`report ${res.status}`);
      setStatus("sent");
      setTimeout(onClose, 1800);
      return;
    } catch {
      // Worker unreachable → fall back to the prefilled GitHub issue so the report isn't lost.
      try {
        await openGithubFallback();
        setStatus("sent");
        setTimeout(onClose, 1800);
      } catch {
        setStatus("failed");
      }
    }
  }

  const message =
    status === "sent" ? "Thank you — your report's been sent! 🙏" :
    status === "failed" ? "Couldn't send — please check your connection and try again." : null;

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
          {status === "sending" ? "Sending…" : "Send"}
        </button>
      </div>
    </div>
  );
}
