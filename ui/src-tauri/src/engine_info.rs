use std::net::TcpListener;

// Per-session engine address + auth token for the loopback sidecar. Generated ONCE at
// startup and held in managed state; crash-respawns reuse the same port+token so the UI
// never has to re-fetch engine_info or update its base URL. Do NOT move pick_port()/
// gen_token() into spawn_engine — that would mint new values on every respawn and break
// the UI's cached token.
#[derive(Clone, serde::Serialize)]
pub struct EngineInfo {
    pub port: u16,
    pub token: String,
}

// First free loopback port in 8765..=8775, or None if all are taken. The caller logs +
// decides the fallback so a port exhaustion isn't a silent dead-end.
pub fn pick_port() -> Option<u16> {
    (8765u16..=8775).find(|&p| TcpListener::bind(("127.0.0.1", p)).is_ok())
}

pub fn gen_token() -> String {
    uuid::Uuid::new_v4().simple().to_string()
}

#[tauri::command]
pub fn engine_info(state: tauri::State<EngineInfo>) -> EngineInfo {
    state.inner().clone()
}
