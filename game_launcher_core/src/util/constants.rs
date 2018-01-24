//! Centralized definition of all heuristic tuning parameters
//!
//! **TODO:** Figure out the most appropriate degree and mechanism for allowing overrides

use regex::Regex;
use cpython::{PyModule, PyResult, Python};

/// Globs denoting supporting binaries which should be excluded from listings
///
/// **TODO:** Decide how to incorporate these without messing up detection of
/// things we actually want:
///
/// `*~`, `java/`, `Mono`, `.mojosetup/*`, `node_modules`, `Shaders`, `uninstall-*`
pub const IGNORED_BINARIES: &[&str] =
    &["xdg-*", "flashplayer", "Data.*", "lib*.so.*", "README*"];

/// File extensions which denote a likely game installer
///
/// **NOTE:** These will be compared against the output of `to_lowercase()`
pub const INSTALLER_EXTS: &[&str] = &[
    "7z", "zip", "rar",
    "tar", "gz", "tgz", "bz2", "tbz2", "xz", "txz",
    "sh",  "run", "bin",
    "deb", "rpm",
    "msi"
];

/// Don't search for metadata inside scripts like `start.sh` if they're bigger
/// than this size.
// Silence spurious warning from clippy bug #1761
#[cfg_attr(feature="cargo-clippy", allow(integer_arithmetic))]
pub const MAX_SCRIPT_SIZE: u64 = 1024 * 1024; // 1 MiB

/// Extensions which indicate files shouldn't be considered as executables even when marked `+x`
///
/// **NOTE:** These will be compared against the output of `to_lowercase()`
pub const NON_BINARY_EXTS: &[&str] = &[
    "dll", "so", "dso", "shlib", "o", "dylib",
    "ini", "xml", "txt",
    "assets", "u", "frag", "vert", "fxg", "xnb", "xsb", "xwb", "xgs",
    "usf", "msf", "asi", "fsb", "fev", "mdd", "lbx", "zmp",
    "as", "cpp", "c", "h", "java",
    "ogg", "mp3", "wav", "spc", "mid", "midi", "rmi",
    "png", "bmp", "gif", "jpg", "jpeg", "svg", "tga", "pcx",
    "pdf",
    "ttf", "crt",
    "dl_", "sc_", "ex_",
];

/// Extensions which denote likely candidates for the launcher menu
///
/// **NOTE:** `.com` is intentionally excluded because they're so rare outside
///           of [DOSBox](http://www.dosbox.com/information.php?page=0)
///           and I worry about the potential for false positives
///           caused by it showing up in some game's web-related clever title.
///
/// **NOTE:** These will be compared against the output of `to_lowercase()`
///
/// **TODO:** Find some way to do a coverage test for this.
pub const PROGRAM_EXTS: &[&str] = &[
    "air", "swf", "jar",
    "sh", "py", "pl",
    "exe", "bat", "cmd", "pif",
    "bin",
    "desktop",
    "love",
    "nes",
];

/// **TODO:** What does the fallback guesser use this for again?
pub const RESOURCE_DIRS: &[&str] =
    &["assets", "data", "*_data", "resources", "icons"];

/// Characters which should prompt `titlecase_up` to uppercase the next one.
///
/// **NOTE:** If titlecasing ever becomes a bottleneck or I feel like micro-optimizing just to
/// amuse myself, I should be able to save some inner-loop iterations by reordering this based on
/// the frequency with which these are used within my test corpus to minimize either the median or
/// total number of comparisons before the algorithm terminates.
pub const WORD_BOUNDARY_CHARS: &str = ". _-";

/// Overrides for common places where the `filename_to_name` heuristic breaks
///
/// **WARNING:** Future versions of the `regex` crate may add an optimization which breaks this.
///    The necessary fix is documented in the code which uses this but has been deferred due to
///    the added hassle of testing it before said optimizations actually exist.
///
/// TODO: Make sure I'm testing all of these cases
/// TODO: Find some way to do a coverage test for this.
pub const WHITESPACE_OVERRIDES: &[(&str, &str)] = &[
    // Keepers (may still be refactored or obsoleted)
    (" - ", ": "),
    (r"Add Ons", "Add-ons"),
    (r"\b3 D\b", "3D"),
    (r": Bit\b", "-Bit"),
    (r"\bDon T", "Don't"), // TODO: Generalize this to more types of contractions
    (r"\bGot Y\b", "GotY"),
    (r"Inc($|[ ])", "Inc.$1"),
    (r"([^:]) Issue\b", r"$1: Issue"), // TODO: Consider making colon insertion a separate ruleset
    (r": Km\b", "km"),
    ("Mc ", "Mc"),
    ("Mac ", "Mac"),
    ("rys ", "ry's "), // TODO: Generalize this to a broader set of posessives
    (r"RO Ms\b", "ROMs"),
    (" S ", "'s "),
    (r"The (\d+):", "The $1"),
    (r": Games", " Games"),
    (r"Vs\.?", "vs."),
    (r"\bMP 3\b", "MP3"),
    (r"\bX (\d)\b", "X$1"),

    // Number suffixes like 2nd
    // TODO: Come up with a more specialized, optimized number suffix handler which can run before
    // the colon insertion phase
    (r": St\b", "st"),
    (r": Nd\b", "nd"),
    (r": Rd\b", "rd"),
    (r": Th\b", "th"),

    // French articles which show up in loan phrases and should be unambiguously matchable
    // TODO: Come up with a solution that allows case-adjustment
    // Source: https://www.thoughtco.com/understanding-french-accents-1369540
    (r"\b([LD]) ([AaÀàÂâEeÈèÉéÊêËëIiÎîÏïOoÔôUuÙùÛûÜü])", "${1}'${2}"),

    // Special cases so common as to be tentatively included
    ("DOS Box", "DOSBox"),
    ("Mupen 64: Plus", "Mupen64Plus"),
    ("Scumm VM", "ScummVM"),
    ("Sid Meiers ", "Sid Meier's "),
    ("^Sim ", "Sim"),
    ("Star Wars ", "Star Wars: "), // TODO: Consider making colon insertion a separate ruleset
    ("Wh 40 K ", "WarHammer 40,000: "),
    (r"Xcom\b", "X-COM:"),

    // TODO: What was this supposed to do again?
    (r": The\b", ": The"),

    // TODO: Once _WS_OVERRIDE_MAP is smarter, add these rules:
    // (r"\b(An? [^ ][^ '])s\b", "\1's"),
    // (r"(\d) (st|nd|th)\b", "\1\2"),

    // Un-audited
    (r" ([A-Z])edit\b", "${1}edit"),
    ("^Open ", "Open"),
    (" V M", "VM"),
    ("xwb", "XWB"),  // TODO: Un-break the support for this in the capitalization forcer
];

/// Simple deduplication helper for `.expect()`-ing a lot of `Regex::new()` calls.
const RE_EXPECT_MSG: &str = "compiled regex from string literal";
lazy_static! {
    // TODO: Unit tests for these regexes, independent from the functional test corpus
    // TODO: Move version-matching into its own pass so we can split on periods

    pub static ref RECOGNIZED_EXTS: Vec<&'static str> =
        [PROGRAM_EXTS, INSTALLER_EXTS, NON_BINARY_EXTS, &["app"]].concat();

    pub static ref WHITESPACE_OVERRIDES_RE: Vec<(Regex, &'static str)> =
        WHITESPACE_OVERRIDES.iter().map(|&(re_str, repl)|
            (Regex::new(re_str).expect(RE_EXPECT_MSG), repl)).collect::<Vec<_>>();

    // TODO: Refactor the stuff below further to minimize the unnecessary use of regexes

    /// Used by `filename_to_name` to insert colons
    pub static ref SUBTITLE_START_RE: Regex = Regex::new(r"(\d)\s+(\w)").expect(RE_EXPECT_MSG);
    /// Used by `filename_to_name` to collapse duplicated whitespace
    pub static ref WHITESPACE_RE: Regex = Regex::new(r"\s+").expect(RE_EXPECT_MSG);

    // Un-refactored stuff below

    /// Used by `filename_to_name` to convert dashes and underscores without duplicating spaces
    pub static ref FNAME_WSPACE_RE: Regex = Regex::new(r"(\s|[_-])+").expect(RE_EXPECT_MSG);
    /// Used by `filename_to_name` to convert just underscores without duplicating spaces
    pub static ref FNAME_WSPACE_NODASH_RE: Regex = Regex::new(r"(\s|[_])+").expect(RE_EXPECT_MSG);
}

/// **TODO:** Figure out how to get the `PyModule::new` and the return into the macro
pub fn into_python_module(py: &Python) -> PyResult<PyModule> {
    let py = *py;
    let py_constants = PyModule::new(py, "constants")?;
    python_reexport!(py, py_constants,
                     WHITESPACE_OVERRIDES,
                     IGNORED_BINARIES, INSTALLER_EXTS,
                     MAX_SCRIPT_SIZE, NON_BINARY_EXTS,
                     PROGRAM_EXTS, RESOURCE_DIRS, WORD_BOUNDARY_CHARS);
    Ok(py_constants)
}
