import { Component, type ErrorInfo, type ReactNode } from "react";
import { APP_VERSION, WORKER_URL } from "../config";
import { openExternal } from "../lib/openExternal";

const REPO = "nandanpugalia/FilingForge";

// Top-level safety net: a render/effect crash anywhere below this boundary shows a
// themed, recoverable message instead of white-screening the whole app (the report
// overlay would be gone too). React unmounts the subtree on an uncaught error, so
// without this the user gets a blank window and no way out. Crucially it ALSO lets the
// user report the crash — the in-app report button is gone once the app has crashed.
type Props = { children: ReactNode };
type State = { crashed: boolean; message: string; reportStatus: "idle" | "sending" | "sent" };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { crashed: false, message: "", reportStatus: "idle" };

  static getDerivedStateFromError(error: Error): State {
    return { crashed: true, message: error?.message ?? "Unknown error", reportStatus: "idle" };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep a console record for the report flow / dev tools; never rethrow.
    console.error("FilingForge crashed:", error, info.componentStack);
  }

  // Opening a prefilled GitHub issue — the FALLBACK if the Worker is unreachable.
  private openGithubFallback = () => {
    const ua = typeof navigator !== "undefined" ? navigator.userAgent : "unknown";
    const title = `[Crash] ${this.state.message.slice(0, 60)}`;
    const body = [
      "FilingForge crashed.", "", "---",
      `- **Error:** ${this.state.message}`,
      `- **App version:** ${APP_VERSION}`,
      `- **System:** ${ua}`,
      "", "_What were you doing when it happened?_",
    ].join("\n");
    return openExternal(
      `https://github.com/${REPO}/issues/new` +
      `?labels=${encodeURIComponent("bug,crash")}` +
      `&title=${encodeURIComponent(title)}` +
      `&body=${encodeURIComponent(body)}`);
  };

  // Same route as the normal report flow: POST to the Worker, which files the GitHub issue
  // server-side (no GitHub account needed). Falls back to the browser issue if offline.
  private report = async () => {
    if (this.state.reportStatus !== "idle") return;
    this.setState({ reportStatus: "sending" });
    const ua = typeof navigator !== "undefined" ? navigator.userAgent : "unknown";
    try {
      const res = await fetch(`${WORKER_URL}/report`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          type: "bug", comment: `App crashed: ${this.state.message}`,
          version: APP_VERSION, screen: "crash", os: ua,
        }),
      });
      if (!res.ok) throw new Error(`report ${res.status}`);
      this.setState({ reportStatus: "sent" });
    } catch {
      try { await this.openGithubFallback(); this.setState({ reportStatus: "sent" }); }
      catch { this.setState({ reportStatus: "idle" }); }
    }
  };

  render() {
    if (!this.state.crashed) return this.props.children;
    return (
      <div className="crash" role="alert">
        <h2 className="crash-title">Something broke.</h2>
        <p className="crash-body">
          FilingForge hit an unexpected error. Your library on disk is untouched —
          reloading the window usually fixes it.
        </p>
        <div className="crash-actions">
          <button className="crash-reload" onClick={() => window.location.reload()}>
            Reload FilingForge
          </button>
          <button className="crash-report" onClick={this.report}
            disabled={this.state.reportStatus !== "idle"}>
            {this.state.reportStatus === "sending" ? "Reporting…"
              : this.state.reportStatus === "sent" ? "Reported — thank you 🙏"
              : "Report this"}
          </button>
        </div>
      </div>
    );
  }
}
