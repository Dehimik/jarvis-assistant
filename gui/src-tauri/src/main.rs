#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
};
use tauri::{AppHandle, Manager, RunEvent, WindowEvent};

struct Backend(Arc<Mutex<Option<Child>>>);

fn start_backend() -> Child {
    // Підстав свій модуль, якщо не server:app
    let mut cmd = Command::new("python");
    cmd.args([
        "-m",
        "uvicorn",
        "assistant.bus.server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]);
    cmd.stdout(Stdio::null()).stderr(Stdio::null());
    cmd.spawn().expect("failed to start backend")
}

fn kill_backend(app: &AppHandle) {
    let state: tauri::State<Backend> = app.state::<Backend>();
    // Обмежуємо lifetime guard'а окремим блоком
    {
        let mut slot = state.0.lock().unwrap();
        if let Some(mut child) = slot.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
    } // <- тут MutexGuard дропнеться до виходу з функції
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // стартуємо бекенд разом з GUI
            let child = start_backend();
            app.manage(Backend(Arc::new(Mutex::new(Some(child)))));
            Ok(())
        })
        // отримаємо саме Window тут, тому беремо AppHandle з нього
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                kill_backend(&window.app_handle());
            }
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        // дублюємо глушіння на всякий випадок при Exit
        .run(|app, event| {
            if let RunEvent::Exit = event {
                kill_backend(&app.app_handle());
            }
        });
}
