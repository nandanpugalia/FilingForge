use serde::Serialize;
use tauri_plugin_updater::UpdaterExt;

// Shared event names — Rust emits these and the TS side (useUpdate.ts) must listen()
// to the exact same strings, so keeping them as one source of truth prevents drift.
pub const EVT_PROGRESS: &str = "update://progress";
pub const EVT_DONE: &str = "update://done";

const STABLE: &str = "https://github.com/nandanpugalia/FilingForge/releases/latest/download/latest.json";
const BETA: &str = "https://nandanpugalia.github.io/FilingForge/latest-beta.json";

pub fn feed(beta: bool) -> &'static str { if beta { BETA } else { STABLE } }

#[derive(Serialize)]
pub struct UpdateInfo { pub version: String, pub notes: Option<String> }

#[tauri::command]
pub async fn check_for_update(app: tauri::AppHandle, beta: bool) -> Result<Option<UpdateInfo>, String> {
    let updater = app
        .updater_builder()
        .endpoints(vec![feed(beta).parse().map_err(|e| format!("bad feed url: {e}"))?])
        .map_err(|e| format!("endpoints: {e}"))?
        .build()
        .map_err(|e| format!("build: {e}"))?;
    match updater.check().await {
        Ok(Some(u)) => Ok(Some(UpdateInfo { version: u.version.clone(), notes: u.body.clone() })),
        Ok(None) => Ok(None),
        Err(e) => Err(format!("{e}")),
    }
}

#[tauri::command]
pub async fn install_update(app: tauri::AppHandle, beta: bool) -> Result<(), String> {
    use std::sync::{atomic::{AtomicUsize, Ordering}, Arc};
    use tauri::Emitter;
    let updater = app
        .updater_builder()
        .endpoints(vec![feed(beta).parse().map_err(|e| format!("bad feed url: {e}"))?])
        .map_err(|e| format!("endpoints: {e}"))?
        .build()
        .map_err(|e| format!("build: {e}"))?;
    let update = updater
        .check().await.map_err(|e| format!("check: {e}"))?
        .ok_or_else(|| "no update available".to_string())?;
    let downloaded = Arc::new(AtomicUsize::new(0));
    let d = downloaded.clone();
    let app_progress = app.clone();
    let app_done = app.clone();
    update
        .download_and_install(
            move |chunk: usize, total: Option<u64>| {
                let n = d.fetch_add(chunk, Ordering::Relaxed) + chunk;
                let pct = total.map(|t| (n as f64 / t as f64 * 100.0) as u32).unwrap_or(0);
                let _ = app_progress.emit(EVT_PROGRESS, pct);
            },
            move || { let _ = app_done.emit(EVT_DONE, ()); },
        )
        .await
        .map_err(|e| format!("install: {e}"))?;
    // The new version is now on disk; relaunch into it. Without this the UI sits forever on
    // "restarting…" and the user must quit + reopen manually. restart() never returns (-> !),
    // so it is the function's tail — nothing after it runs.
    app.restart()
}

#[cfg(test)]
mod tests {
    use super::{feed, BETA, STABLE};

    #[test]
    fn stable_installs_never_read_the_prerelease_feed() {
        assert_eq!(feed(false), STABLE);
        assert_ne!(feed(false), BETA);
    }

    #[test]
    fn opted_in_installs_read_only_the_prerelease_feed() {
        assert_eq!(feed(true), BETA);
        assert_ne!(feed(true), STABLE);
    }
}
