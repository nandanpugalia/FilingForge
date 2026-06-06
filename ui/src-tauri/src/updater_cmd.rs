use serde::Serialize;
use tauri_plugin_updater::UpdaterExt;

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
