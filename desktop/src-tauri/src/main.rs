// K-Creative Studio Desktop — Tauri shell
// Launches the FastAPI backend and wraps the web UI in a native window.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;

struct BackendProcess(Mutex<Option<Child>>);

fn start_backend() -> Option<Child> {
    let studio_dir = "/home/raphael/K-Creative-Cloud/studio";
    Command::new("python3")
        .arg("server.py")
        .current_dir(studio_dir)
        .spawn()
        .ok()
}

fn main() {
    let backend = start_backend();

    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(backend)))
        .on_window_event(|event| {
            if let tauri::WindowEvent::Destroyed = event.event() {
                // Backend cleanup happens via process group on app exit
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
