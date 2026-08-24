mod engine_info;
mod updater_cmd;

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

// Engine lifecycle state. `child` holds the live sidecar handle (if any); `shutting_down`
// is set just before we kill the engine on window close, so the crash-monitor below does
// NOT resurrect the very process we intentionally terminated.
struct EngineState {
    child: Mutex<Option<CommandChild>>,
    shutting_down: AtomicBool,
}

// Spawn the bundled Python engine sidecar and monitor it. If it dies UNEXPECTEDLY mid-session
// (crash, OOM, killed), respawn it up to a small cap so the app doesn't become a permanent
// dead shell. Failure to spawn at all is logged, NOT panicked — the window still opens and the
// UI's ReadyGate surfaces a friendly "couldn't reach the engine" screen after its health timeout.
fn spawn_engine(app: tauri::AppHandle, attempt: u32) {
    const MAX_RESTARTS: u32 = 5;

    let info = app.state::<engine_info::EngineInfo>();
    let (port, token) = (info.port, info.token.clone());
    let command = match app.shell().sidecar("filingforge-api") {
        Ok(c) => c.env("FF_PORT", port.to_string()).env("FF_TOKEN", token),
        Err(e) => {
            eprintln!("[engine] sidecar binary 'filingforge-api' not found: {e}");
            return;
        }
    };
    let (mut rx, child) = match command.spawn() {
        Ok(pair) => pair,
        Err(e) => {
            eprintln!("[engine] failed to spawn engine sidecar: {e}");
            return;
        }
    };
    *app.state::<EngineState>().child.lock().unwrap() = Some(child);

    // Watch the event stream; the only event we act on is Terminated.
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            if matches!(event, CommandEvent::Terminated(_)) {
                let state = app.state::<EngineState>();
                if state.shutting_down.load(Ordering::SeqCst) {
                    return; // app is closing — this was our own kill, don't respawn
                }
                if attempt >= MAX_RESTARTS {
                    eprintln!(
                        "[engine] sidecar exited and hit the restart cap ({MAX_RESTARTS}); giving up — the UI will show the engine-unreachable screen."
                    );
                    return;
                }
                eprintln!(
                    "[engine] sidecar exited unexpectedly; respawning (attempt {}/{})",
                    attempt + 1,
                    MAX_RESTARTS
                );
                spawn_engine(app.clone(), attempt + 1);
                return; // the new spawn owns the new child + monitor
            }
        }
    });
}

// Idempotent so it is safe to call from both the window lifecycle and the app
// event loop. macOS Cmd+Q can exit the application without delivering the
// window Destroyed event, so cleanup must not live only in on_window_event.
fn stop_engine(app: &tauri::AppHandle) {
    let state = app.state::<EngineState>();
    state.shutting_down.store(true, Ordering::SeqCst);
    let taken = state.child.lock().unwrap().take();
    if let Some(child) = taken {
        // child.kill() only terminates the DIRECT sidecar process. PyInstaller's
        // one-file bootloader spawns a worker child that runs uvicorn and holds
        // the port — terminate the whole process tree.
        let pid = child.pid();
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            let _ = std::process::Command::new("taskkill")
                .args(["/PID", &pid.to_string(), "/T", "/F"])
                .creation_flags(CREATE_NO_WINDOW)
                .status();
            let _ = child;
        }
        #[cfg(not(target_os = "windows"))]
        {
            // A uvicorn worker can keep handling SIGTERM while its PyInstaller
            // parent exits and is reparented to launchd. Force-stop that exact
            // direct child before terminating the bootloader.
            let _ = std::process::Command::new("pkill")
                .args(["-KILL", "-P", &pid.to_string()])
                .status();
            let _ = child.kill();
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        // Single-instance MUST be the first plugin registered. When a 2nd copy of the
        // app launches, this callback fires in the ALREADY-running instance (the 2nd
        // process exits immediately) — so we never spawn a competing engine sidecar on
        // 127.0.0.1:8765. We just surface the existing window.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.unminimize();
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        // Auto-update: checks the signed feed in tauri.conf.json > plugins.updater.
        // process plugin provides relaunch() after an update installs.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(engine_info::EngineInfo {
            port: engine_info::pick_port().unwrap_or_else(|| {
                eprintln!("[engine] no free port in 8765–8775; defaulting to 8765");
                8765
            }),
            token: engine_info::gen_token(),
        })
        .manage(EngineState {
            child: Mutex::new(None),
            shutting_down: AtomicBool::new(false),
        })
        .invoke_handler(tauri::generate_handler![
            updater_cmd::check_for_update,
            updater_cmd::install_update,
            engine_info::engine_info
        ])
        .setup(|app| {
            // Spawn the engine on startup. Errors are logged, not panicked (see spawn_engine).
            spawn_engine(app.handle().clone(), 0);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                stop_engine(window.app_handle());
            }
        })
        .build(tauri::generate_context!());

    match app {
        Ok(app) => app.run(|app, event| {
            // Cmd+Q on macOS requests application exit without necessarily
            // destroying the main window first. Clean up at the app lifecycle
            // boundary as well as the window boundary.
            if matches!(event, tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit) {
                stop_engine(app);
            }
        }),
        Err(e) => {
            // Don't panic on a setup error — log and exit cleanly.
            eprintln!("FilingForge failed to start: {e}");
        }
    }
}
