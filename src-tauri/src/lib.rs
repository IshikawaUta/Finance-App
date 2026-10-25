use pyo3::prelude::*;

/// Copy build-time configuration into the process environment.
///
/// GitHub Actions injects the MongoDB URI, database name and timezone while
/// compiling the Rust binary (`option_env!`). At runtime the Python layer reads
/// environment variables, so we expose the baked-in values only when the
/// corresponding variable is not already set. A `config.json` written by the
/// login setup dialog or Settings still has the highest priority (see
/// `finance_app/config.py`).
pub fn inject_build_config() {
    const BUILD_CONFIG: [(&str, Option<&str>); 3] = [
        ("FINANCE_MONGODB_URI", option_env!("FINANCE_MONGODB_URI")),
        ("FINANCE_MONGODB_DB", option_env!("FINANCE_MONGODB_DB")),
        ("FINANCE_TIMEZONE", option_env!("FINANCE_TIMEZONE")),
    ];

    for (key, value) in BUILD_CONFIG {
        let Some(value) = value.map(str::trim).filter(|value| !value.is_empty()) else {
            continue;
        };
        if std::env::var_os(key).is_none() {
            std::env::set_var(key, value);
        }
    }
}

pub fn tauri_generate_context() -> tauri::Context {
    inject_build_config();
    tauri::generate_context!()
}

#[pymodule(gil_used = false)]
#[pyo3(name = "ext_mod")]
pub mod ext_mod {
    use super::*;

    #[pymodule_init]
    fn init(module: &Bound<'_, PyModule>) -> PyResult<()> {
        pytauri::pymodule_export(
            module,
            // Called by Python as `pytauri.context_factory()`.
            |_args, _kwargs| Ok(tauri_generate_context()),
            // Called by Python as `pytauri.builder_factory()`.
            |_args, _kwargs| Ok(tauri::Builder::default()),
        )
    }
}
