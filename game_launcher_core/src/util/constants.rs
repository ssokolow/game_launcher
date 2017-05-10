//! Centralized definition of all heuristic tuning parameters
//!
//! **TODO:** Figure out the most appropriate degree and mechanism for allowing overrides

use cpython::{PyModule, PyResult, Python};

/// Globs denoting supporting binaries which should be excluded from listings
///
/// TODO: Decide how to incorporate these without messing up detection of
///  things we actually want:
///
///  .mojosetup/*, uninstall-*, java/, node_modules, Shaders, *~, Mono
pub const IGNORED_BINARIES: &'static [&'static str] =
    &["xdg-*", "flashplayer", "Data.*", "lib*.so.*", "README*"];

/// Extensions which denote a likely game installer
pub const INSTALLER_EXTS: &'static [&'static str] = &[
    ".zip", ".rar",
    ".tar", ".gz", ".tgz", ".bz2", ".tbz2", ".xz", ".txz",
    ".sh",  ".run", ".bin",
    ".deb", ".rpm"
];

/// Don't search for metadata inside scripts like "start.sh" if they're bigger
/// than this size.
pub const MAX_SCRIPT_SIZE: u64 = 1024 * 1024; // 1 MiB

/// Extensions which indicate files shouldn't be considered as executables even when marked +x
pub const NON_BINARY_EXTS: &'static [&'static str] = &[
    ".dll", ".so", ".dso", ".shlib", ".o", ".dylib",
    ".ini", ".xml", ".txt",
    ".assets", ".u", ".frag", ".vert", ".fxg", ".xnb", ".xsb", ".xwb", ".xgs",
    ".usf", ".msf", ".asi", ".fsb", ".fev", ".mdd", ".lbx", ".zmp",
    ".as", ".cpp", ".c", ".h", ".java",
    ".ogg", ".mp3", ".wav", ".spc", ".mid", ".midi", ".rmi",
    ".png", ".bmp", ".gif", ".jpg", ".jpeg", ".svg", ".tga", ".pcx",
    ".pdf",
    ".ttf", ".crt",
    ".dl_", ".sc_", ".ex_",
];

/// Extensions which denote likely candidates for the launcher menu
///
/// Note: `.com` is intentionally excluded because they're so rare outside
///       of DOSBox and I worry about the potential for false positives
///       caused by it showing up in some game's clever title.
///
/// TODO: Find some way to do a coverage test for this.
pub const PROGRAM_EXTS: &'static [&'static str] = &[
    ".air", ".swf", ".jar",
    ".sh", ".py", ".pl",
    ".exe", ".bat", ".cmd", ".pif",
    ".bin",
    ".desktop",
];

// TODO: What does the fallback guesser use this for again?
pub const RESOURCE_DIRS: &'static [&'static str] =
    &["assets", "data", "*_data", "resources", "icons"];

/// TODO: Figure out how to get the `PyModule::new` and the return into the macro
pub fn into_python_module(py: &Python) -> PyResult<PyModule> {
    let py = *py;
    let py_constants = PyModule::new(py, "constants")?;
    python_reexport!(py, py_constants,
                     IGNORED_BINARIES, INSTALLER_EXTS,
                     MAX_SCRIPT_SIZE, NON_BINARY_EXTS,
                     PROGRAM_EXTS, RESOURCE_DIRS);
    Ok(py_constants)
}
