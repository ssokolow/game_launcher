//! TODO: Refactor the Python dependency out

use cpython::{PyModule, PyResult, Python};

pub mod constants {
    /// Support binaries which whould be excluded from listings
    pub const IGNORED_BINARIES: &'static [&'static str] = &[
        "xdg-*", "flashplayer",
        "Data.*",
        "lib*.so.*",
        "README*",
    ];

    /// Extensions which denote a likely game installer
    pub const INSTALLER_EXTS: &'static [&'static str] = &[
        ".zip", ".rar",
        ".tar", ".gz", ".tgz", ".bz2", ".tbz2", ".xz", ".txz",
        ".sh",  ".run", ".bin",
        ".deb", ".rpm"
    ];

    /// Don't search for metadata inside scripts like "start.sh" if they're bigger
    /// than this size.
    pub const MAX_SCRIPT_SIZE: usize = 1024 * 1024;  // 1 MiB

    /// Files which shouldn't be considered as executables even when marked +x
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
    // TODO: .mojosetup/*, uninstall-*, java/, node_modules, xdg-*, Shaders, *~, Mono

    // TODO: Find some way to do a coverage test for this.
    /// Extensions which denote a likely candidate for the launcher menu
    pub const PROGRAM_EXTS: &'static [&'static str] = &[
        ".air", ".swf", ".jar",
        ".sh", ".py", ".pl",
        ".exe", ".bat", ".cmd", ".pif",
        ".bin",
        ".desktop",
        // Note: .com is intentionally excluded because they're so rare outside of
        //       DOSBox and I worry about the potential for false positives caused
        //       by it showing up in some game's clever title.
    ];

    // TODO: What does the fallback guesser use this for again?
    pub const RESOURCE_DIRS: &'static [&'static str] = &[
        "assets",
        "data", "*_data",
        "resources",
        "icons",
    ];
}

pub mod executables {
    pub enum Role {
        Play = -2,
        Configure,
        Unknown,
        Update,
        Install,
        Uninstall
    }
    // TODO: Implement ToPyObject
}

pub fn get_python_module(py: &Python) -> PyResult<PyModule> {
    let py = *py;
    // TODO: come up with a macro to remove all of this republishing boilerplate
    let py_constants = try!(PyModule::new(py, "constants"));
    try!(py_constants.add(py, "IGNORED_BINARIES", constants::IGNORED_BINARIES));
    try!(py_constants.add(py, "INSTALLER_EXTS", constants::INSTALLER_EXTS));
    try!(py_constants.add(py, "NON_BINARY_EXTS", constants::NON_BINARY_EXTS));
    try!(py_constants.add(py, "PROGRAM_EXTS", constants::PROGRAM_EXTS));
    try!(py_constants.add(py, "RESOURCE_DIRS", constants::RESOURCE_DIRS));

    let py_util = try!(PyModule::new(py, "util"));
    try!(py_util.add(py, "constants", py_constants));
    Ok(py_util)
}
