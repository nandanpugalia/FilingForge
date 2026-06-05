import { Component, type ErrorInfo, type ReactNode } from "react";

// Top-level safety net: a render/effect crash anywhere below this boundary shows a
// themed, recoverable message instead of white-screening the whole app (the report
// overlay would be gone too). React unmounts the subtree on an uncaught error, so
// without this the user gets a blank window and no way out.
type Props = { children: ReactNode };
type State = { crashed: boolean };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { crashed: false };

  static getDerivedStateFromError(): State {
    return { crashed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep a console record for the report flow / dev tools; never rethrow.
    console.error("FilingForge crashed:", error, info.componentStack);
  }

  render() {
    if (!this.state.crashed) return this.props.children;
    return (
      <div className="crash" role="alert">
        <h2 className="crash-title">Something broke.</h2>
        <p className="crash-body">
          FilingForge hit an unexpected error. Your library on disk is untouched —
          reloading the window usually fixes it.
        </p>
        <button className="crash-reload" onClick={() => window.location.reload()}>
          Reload FilingForge
        </button>
      </div>
    );
  }
}
