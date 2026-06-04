import { useReducer, useState, useEffect, useRef } from "react";
import "./theme.css";
import { reducer, initialState } from "./flow";
import { startBuild, subscribeBuildEvents, getStatus, openFolder, getLibrary } from "./api";
import { loadSettings, saveSettings } from "./settings";
import { tickerFor } from "./lib/ticker";
import type { BuildScope, BuildResult, Settings } from "./types";
import { TitleBar } from "./components/TitleBar";
import { SearchField } from "./components/SearchField";
import { ConfigPanel } from "./components/ConfigPanel";
import { ProgressView } from "./components/ProgressView";
import { DoneView } from "./components/DoneView";
import { ErrorView } from "./components/ErrorView";
import { SettingsOverlay } from "./components/SettingsOverlay";
import { LibraryOverlay } from "./components/LibraryOverlay";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [settings, setSettings] = useState<Settings>(loadSettings());
  const [dest, setDest] = useState(settings.dest);
  const [showSettings, setShowSettings] = useState(false);
  const [showLibrary, setShowLibrary] = useState(false);
  const [hasLibrary, setHasLibrary] = useState(false);
  const [starting, setStarting] = useState(false);
  const settingsRef = useRef(settings); settingsRef.current = settings;
  const sub = useRef<{ close(): void } | null>(null);
  const lastScope = useRef<BuildScope | null>(null);
  const inFlight = useRef(false); // R7: double-build guard

  const refreshLibrary = () =>
    getLibrary(settingsRef.current.dest).then((c) => setHasLibrary(c.length > 0)).catch(() => setHasLibrary(false));
  useEffect(() => { refreshLibrary(); return () => sub.current?.close(); }, []);   // mount + cleanup

  async function build(scope: BuildScope) {
    if (inFlight.current) return;   // R7: ignore re-entrant builds (double-click / rapid retry)
    inFlight.current = true;
    lastScope.current = scope;
    setStarting(true);
    try {
      const jobId = await startBuild(scope);
      dispatch({ type: "START_BUILD", jobId });
      setStarting(false);
      sub.current?.close();
      sub.current = subscribeBuildEvents(jobId, {
        onProgress: (p) => dispatch({ type: "PROGRESS", progress: p }),
        onEnd: async (tail) => {
          let result = tail?.result as BuildResult | undefined;
          let status = tail?.status;
          let error = tail?.error;
          if (!result && status !== "error") {
            try { const st = await getStatus(jobId); result = st.result ?? undefined; status = st.status; error = st.error; }
            catch { /* */ }
          }
          inFlight.current = false;
          if (status === "error") dispatch({ type: "FAIL", message: error || "Build failed. Please try again." });
          else if (result) {
            dispatch({ type: "BUILD_DONE", result });
            if (settingsRef.current.openWhenDone) openFolder(`${scope.dest}/${scope.ticker}`).catch(() => {});
            refreshLibrary();
          } else dispatch({ type: "FAIL", message: "Build ended unexpectedly. Please try again." });
        },
      });
    } catch (e) { inFlight.current = false; setStarting(false); dispatch({ type: "FAIL", message: (e as Error).message }); }
  }

  return (
    <div className="app">
      <TitleBar showLibrary={hasLibrary}
        onSettings={() => setShowSettings(true)} onLibrary={() => setShowLibrary(true)} />
      <main className="stage">
        {state.phase === "search" && (
          <>
            <p className="tagline">Turn any Indian company's filings into a library your AI can actually read.</p>
            <SearchField onPick={(c) => dispatch({ type: "PICK_COMPANY", candidate: c })} />
          </>
        )}
        {state.phase === "configure" && state.company && (
          <ConfigPanel company={state.company} dest={dest} settings={settings} starting={starting}
            onChangeCompany={() => dispatch({ type: "CHANGE_COMPANY" })} onDestChange={setDest} onBuild={build} />
        )}
        {state.phase === "building" && (
          <ProgressView progress={state.progress} log={state.progressLog}
            onCancel={() => { sub.current?.close(); inFlight.current = false; dispatch({ type: "CHANGE_COMPANY" }); }} />
        )}
        {state.phase === "done" && state.result && state.company && (
          <DoneView ticker={tickerFor(state.company)} result={state.result}
            onOpen={() => openFolder(`${dest}/${tickerFor(state.company!)}`).catch(() => {})}
            onReset={() => dispatch({ type: "RESET" })} />
        )}
        {state.phase === "error" && (
          <ErrorView message={state.error || "Something went wrong."}
            onRetry={() => { if (lastScope.current) build(lastScope.current); else dispatch({ type: "RESET" }); }} />
        )}
      </main>
      <footer className="footer">FilingForge · free &amp; open-source</footer>
      {showSettings && <SettingsOverlay settings={settings}
        onSave={(s) => { setSettings(s); saveSettings(s); setDest(s.dest); }} onClose={() => setShowSettings(false)} />}
      {showLibrary && <LibraryOverlay root={settingsRef.current.dest}
        onOpen={(t) => openFolder(`${settingsRef.current.dest}/${t}`).catch(() => {})} onClose={() => setShowLibrary(false)} />}
    </div>
  );
}
