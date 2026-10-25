// Prevents an additional console window on Windows in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{convert::Infallible, error::Error, path::PathBuf};

use finance_app_lib::{ext_mod, inject_build_config, tauri_generate_context};
use pyo3::wrap_pymodule;
use pytauri::standalone::{
    dunce::simplified, PythonInterpreterBuilder, PythonInterpreterEnv, PythonScript,
};
use tauri::utils::platform::resource_dir;

fn main() -> Result<Infallible, Box<dyn Error>> {
    // Must happen before Python starts: `finance_app.main` reads configuration
    // while creating AppState, before the Tauri context is built.
    inject_build_config();

    let py_env = if cfg!(dev) {
        // `cfg(dev)` is set by tauri-build when launched through `tauri dev`.
        // Prefer an activated virtualenv; fall back to `<repo>/.venv` so the
        // standard `npm run tauri dev` flow works without activation.
        let venv_dir = std::env::var_os("VIRTUAL_ENV")
            .map(PathBuf::from)
            .unwrap_or_else(|| {
                let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
                path.pop();
                path.push(".venv");
                path
            });

        assert!(
            venv_dir.is_dir(),
            "Python virtual environment not found at {}. Create it with \
             `python3 -m venv .venv && .venv/bin/pip install -e .`.",
            venv_dir.display()
        );

        PythonInterpreterEnv::Venv(venv_dir.into())
    } else {
        // Bundled application: Python lives in Tauri's resource directory.
        let context = tauri_generate_context();
        let resource_dir = resource_dir(context.package_info(), &tauri::Env::default())
            .map_err(|err| format!("failed to get resource dir: {err}"))?;
        // Python tooling dislikes the Windows UNC prefix (`\\?\`).
        let resource_dir = simplified(&resource_dir).to_owned();

        PythonInterpreterEnv::Standalone(resource_dir.into())
    };

    // Equivalent to `python -m finance_app`.
    let py_script = PythonScript::Module("finance_app".into());

    // The extension module is exported from memory, so no `.pyd`/`.so` file
    // needs to be written next to the executable.
    let builder =
        PythonInterpreterBuilder::new(py_env, py_script, |py| wrap_pymodule!(ext_mod)(py));
    let interpreter = builder.build()?;

    let exit_code = interpreter.run();
    std::process::exit(exit_code);
}
