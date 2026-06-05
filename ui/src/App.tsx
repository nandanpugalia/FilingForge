import { useReducer, useState, useEffect, useRef } from "react";
import "./theme.css";
import { reducer, initialState } from "./flow";
import { startBuild, subscribeBuildEvents, getStatus, openFolder, getLibrary, resolve } from "./api";
import { loadSettings, saveSettings, isFirstRun } from "./settings";
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
import { ReportOverlay } from "./components/ReportOverlay";
import { SkillsOverlay } from "./components/SkillsOverlay";
import { FirstRunOverlay } from "./components/FirstRunOverlay";
import { UpdateBanner } from "./components/UpdateBanner";
import { useUpdate } from "./lib/useUpdate";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [settings, setSettings] = useState<Settings>(loadSettings());
  const [needsSetup, setNeedsSetup] = useState(isFirstRun());
  // Exactly one overlay open at a time — opening one replaces any other,
  // and its backdrop (z-index 500) covers the titlebar so its icons are
  // not clickable through an open overlay.
  const [overlay, setOverlay] = useState<null | "settings" | "library" | "report" | "skills">(null);
  // One update controller, shared by the top banner and the Settings "Check for updates" button.
  const updater = useUpdate();
  const [hasLibrary, setHasLibrary] = useState(false);
  const [starting, setStarting] = useState(false);
  const [breakdown, setBreakdown] = useState<Record<string, number> | undefined>(undefined);
  // settingsRef gives the long-lived async callbacks (subscribeBuildEvents.onEnd, refreshLibrary)
  // the latest settings without going stale. JSX/inline handlers below use `settings` directly —
  // they're recreated every render, so the ref is only for closures that outlive their render.
  const settingsRef = useRef(settings);
  useEffect(() => { settingsRef.current = settings; }, [settings]);
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
            setBreakdown(undefined);
            getLibrary(scope.dest)
              .then((items) => { const hit = items.find((i) => i.ticker === scope.ticker); setBreakdown(hit?.counts); })
              .catch(() => setBreakdown(undefined));
            if (settingsRef.current.openWhenDone) openFolder(`${scope.dest}/${scope.ticker}`).catch(() => {});
            refreshLibrary();
          } else dispatch({ type: "FAIL", message: "Build ended unexpectedly. Please try again." });
        },
      });
    } catch (e) { inFlight.current = false; setStarting(false); dispatch({ type: "FAIL", message: (e as Error).message }); }
  }

  return (
    <div className="app">
      {needsSetup && (
        <FirstRunOverlay defaultDest={settings.dest} onComplete={(d) => {
          const next = { ...settings, dest: d };
          setSettings(next); saveSettings(next); setNeedsSetup(false);
        }} />
      )}
      <UpdateBanner state={updater.state} install={updater.install} dismiss={updater.dismiss} />
      <TitleBar showLibrary={hasLibrary} showWordmark={state.phase !== "search"}
        onSettings={() => setOverlay("settings")} onLibrary={() => setOverlay("library")}
        onSkills={() => setOverlay("skills")} onReport={() => setOverlay("report")} />
      <main className="stage">
        {state.phase === "search" && (
          <>
            <h1 className="wordmark search-wordmark">FilingForge<span className="wm-dot">.</span></h1>
            <p className="tagline">Turn any BSE-listed company's filings into a clean, AI-ready library.</p>
            <SearchField onPick={(c) => dispatch({ type: "PICK_COMPANY", candidate: c })} />
          </>
        )}
        {state.phase === "configure" && state.company && (
          <ConfigPanel company={state.company} settings={settings} starting={starting}
            onChangeCompany={() => dispatch({ type: "CHANGE_COMPANY" })} onBuild={build} />
        )}
        {state.phase === "building" && (
          <ProgressView progress={state.progress} log={state.progressLog}
            onBack={() => { sub.current?.close(); inFlight.current = false; dispatch({ type: "BACK_TO_CONFIGURE" }); }} />
        )}
        {state.phase === "done" && state.result && state.company && (
          <DoneView ticker={tickerFor(state.company)} name={state.company.company} dest={settings.dest}
            result={state.result} breakdown={breakdown}
            onOpen={() => openFolder(`${settings.dest}/${tickerFor(state.company!)}`).catch(() => {})}
            onReset={() => dispatch({ type: "RESET" })} />
        )}
        {state.phase === "error" && (
          <ErrorView message={state.error || "Something went wrong."}
            onRetry={() => { if (lastScope.current) build(lastScope.current); else dispatch({ type: "RESET" }); }}
            onBack={state.company ? () => dispatch({ type: "BACK_TO_CONFIGURE" }) : undefined}
            onReport={() => setOverlay("report")} />
        )}
      </main>
      {overlay === "settings" && <SettingsOverlay settings={settings} updater={updater}
        onSave={(s) => { setSettings(s); saveSettings(s); }} onClose={() => setOverlay(null)} />}
      {overlay === "library" && <LibraryOverlay root={settings.dest}
        onOpen={(t) => openFolder(`${settings.dest}/${t}`).catch(() => {})} onClose={() => setOverlay(null)}
        onAddCompany={() => { setOverlay(null); dispatch({ type: "RESET" }); }}
        onRefresh={async (ticker) => {
          setOverlay(null);
          try {
            const cands = await resolve(ticker);
            const c = cands.find((x) => x.symbol === ticker) || cands.find((x) => x.is_primary) || cands[0];
            if (!c) { dispatch({ type: "RESET" }); return; }
            dispatch({ type: "PICK_COMPANY", candidate: c });
            build({ scrip_code: c.scrip_code, ticker, dest: settings.dest,
                    years: settings.years, everything: true, categories: [] });
          } catch (e) { dispatch({ type: "FAIL", message: (e as Error).message }); }
        }} />}
      {overlay === "report" && <ReportOverlay screen={state.phase} onClose={() => setOverlay(null)} />}
      {overlay === "skills" && <SkillsOverlay root={settings.dest} onClose={() => setOverlay(null)} />}
    </div>
  );
}
