//!"""Routines for inferring a game's name"""
//!
//! TODO: Refactor the Python dependency out or make it optional

use std::borrow::Cow;
use std::ffi::OsStr;
use std::path::Path;

use regex::Regex;
use cpython::{PyModule, PyResult, Python};

use super::constants::{
    FNAME_WSPACE_RE, FNAME_WSPACE_NODASH_RE, INSTALLER_EXTS,
    PROGRAM_EXTS, SUBTITLE_START_RE, WHITESPACE_RE, WORD_BOUNDARY_CHARS
};


lazy_static! {
    /// Used by naming::camelcase_to_spaces but not intended to be exposed directly
    /// (Included here to keep the tunables together)
    ///
    /// TODO: Move this to super::constants one pub(restricted) is stable
    static ref CAMELCASE_RE: Regex = Regex::new(
        r"([a-z])([A-Z0-9])|([^ ])([A-Z][a-z])|([0-9])([a-z])")
        .expect("compiled regex in string literal");
}

/// Convenience wrapper so the replacement string only needs to exist in one place
pub fn camelcase_to_spaces(in_str: &str) -> Cow<str> {
        CAMELCASE_RE.replace_all(&in_str, "${1}${3}${5} ${2}${4}${6}")
}

/// Helper for `filename_to_name` to strip recognized extensions without over-stripping when
/// periods are used in other ways.
fn _filename_extensionless<P: AsRef<Path> + ?Sized>(path: &P) -> Cow<str> {
    let path = path.as_ref();

    // Use the file_stem() if the extension is present and in `PROGRAM_EXTS`, case-insensitively
    let name = match path.extension().map(|x| x.to_string_lossy().to_lowercase()) {
        Some(ref ext) if PROGRAM_EXTS.contains(&ext.as_str()) => path.file_stem(),
        _ => path.file_name()
    };

    // Ensure we consistently have either an empty string or an escaped string
    // TODO: Is this still simpler than converting empty strings to Option::None early?
    name.unwrap_or_else(|| OsStr::new("")).to_string_lossy()
}

/// A heuristic transform to produce pretty good titles from filenames without relying on
/// out-of-band information.
pub fn filename_to_name<P: AsRef<Path> + ?Sized>(path: &P) -> Option<String> {
    let name_in = _filename_extensionless(path);

    // TODO: Refactor this function for simplicity and early return
    // TODO: Group the algorithm into labelled phases

    // TODO: Remove version information

    // TODO: Maybe I should convert whitespace cues first, then filter out version information in
    //      a wordwise manner.
    let name = normalize_whitespace(&name_in);

    // Assume that a number followed by whitespace and more text marks the beginning of a subtitle
    // and add a colon and normalized space
    let name = SUBTITLE_START_RE.replace_all(&name, "${1}: ${2}");

    // Titlecase... but only in the lower->upper direction so things like "FTL" remain
    let name_in = titlecase_up(&name);

    // Ensure that numbers are preceded by a space (Anticipate two inserted spaces at most)
    let mut name = String::with_capacity(name_in.len() + 2);
    let mut lastchar_was_alpha = false;
    for chara in name_in.chars() {
        if lastchar_was_alpha && chara.is_digit(10) { name.push(' '); }
        lastchar_was_alpha = chara.is_alphabetic();
        name.push(chara);
    }

    // Assume 1-2 character names are either acronyms or "Ys", which is handled by overrides
    if name.len() < 3 {
        name = name.to_uppercase().to_string();
    }

    // TODO: Fix capitalization anomalies broken by whitespace conversion

    // Normalize whitespace which may be left over
    name = WHITESPACE_RE.replace_all(&name, " ").trim().to_string();

    // Return `None` instead of an empty string to make it clear that this can fail.
    // (Whitespace and Unicode replacement characters are excluded from the count)
    match name.chars().filter(|x| !(*x == '\u{FFFD}' || x.is_whitespace())).count() {
        0 => None,
        _ => Some(name)
    }
}

/// Helper for `filename_to_name` to heuristically normalize word-breaks in filenames
/// which may initially be using non-whitespace characters such as underscores or CamelCasing.
pub fn normalize_whitespace(in_str: &str) -> Cow<str> {
    // XXX: Is there a way to avoid doing the bits in is_match() twice in matching branches?
    if FNAME_WSPACE_RE.is_match(in_str) {
        // TODO: Need to ignore `x86_64` when checking for underscores
        if FNAME_WSPACE_NODASH_RE.is_match(in_str) {
            // Make sure things like "X-Com Collection" don't have their dashes converted
            FNAME_WSPACE_NODASH_RE.replace_all(in_str, " ")
        } else {
            // ...but also handle names using dashes as separators properly
            FNAME_WSPACE_RE.replace_all(in_str, " ")
        }
    } else {
        // Handle CamelCase cues
        camelcase_to_spaces(in_str)
    }
}

/// Return a titlecased copy of the input with the following two modifications to the algorithm:
///
/// 1. Never perform upper->lowercase conversion in order to preserve acronyms
/// 2. Treat any character in `WORD_BOUNDARY_CHARS` as preceding a new word.
pub fn titlecase_up(in_str: &str) -> String {
    // Preallocate for the "case-conversion doesn't change length" case common in western langs
    let mut out_str = String::with_capacity(in_str.len());
    let mut lastchar_was_boundary = true;  // The start of the string is a \b

    for chara in in_str.chars() {
        if lastchar_was_boundary {
            out_str.extend(chara.to_uppercase());
        } else {
            out_str.push(chara);
        }
        lastchar_was_boundary = WORD_BOUNDARY_CHARS.chars().any(|x| x == chara);
    }
    out_str
}

// --== CPython API ==--

fn py_camelcase_to_spaces<'a>(_: Python, in_str: &'a str) -> PyResult<String> {
    Ok(camelcase_to_spaces(in_str).into_owned())
}

fn py_normalize_whitespace(_: Python, in_str: &str) -> PyResult<String> {
    Ok(normalize_whitespace(in_str).into_owned())
}

/// rust-cpython API wrapper for `titlecase_up`
fn py_titlecase_up(_: Python, in_str: &str) -> PyResult<String> { Ok(titlecase_up(in_str)) }

/// TODO: Figure out how to get the `PyModule::new` and the return macro-ized
pub fn into_python_module(py: &Python) -> PyResult<PyModule> {
    let py = *py;
    let py_naming = PyModule::new(py, "naming")?;
    py_naming.add(py, "camelcase_to_spaces", py_fn!(py, py_camelcase_to_spaces(in_str: &str)))?;
    py_naming.add(py, "normalize_whitespace", py_fn!(py, py_normalize_whitespace(in_str: &str)))?;
    py_naming.add(py, "titlecase_up", py_fn!(py, py_titlecase_up(in_str: &str)))?;
    Ok(py_naming)
}

#[cfg(test)]
mod tests {
    use super::{camelcase_to_spaces, titlecase_up};

    fn check_titlecase_up(input: &str, expected: &str) {
        let result = titlecase_up(input);
        assert_eq!(result, expected, "(with input {:?})", input);
        assert_eq!(titlecase_up(&result), expected,
                   "titlecase_up should be a no-op when re-run on its own output");
    }

    #[test]
    fn titlecase_up_basic_functionality() {
        // TODO: Make this much more thorough
        check_titlecase_up("hello", "Hello");                             // One word
        check_titlecase_up("testtesttest", "Testtesttest");               // One compound word
        check_titlecase_up("1234567890", "1234567890");                   // All numeric
        // TODO: Mixes of words and numbers  (eg. to test word boundary detection)
        check_titlecase_up("foo_bar_baz_quux", "Foo_Bar_Baz_Quux");       // Lower with underscores
        check_titlecase_up("foo-bar-baz-quux", "Foo-Bar-Baz-Quux");       // Lowercase with dashes
        check_titlecase_up("bit.trip.runner", "Bit.Trip.Runner");         // Lowercase with periods
        check_titlecase_up("green eggs and spam", "Green Eggs And Spam"); // Lowercase with spaces
        // TODO: Various mixes of separator characters
        // TODO: Various mixes of capitalization and separators
        check_titlecase_up("ScummVM", "ScummVM");                         // Unusual capitalization
        check_titlecase_up("FTL", "FTL");                                 // All-uppercase acronym
    }

    #[test]
    fn camelcase_to_spaces_basic_function() {
        assert_eq!(camelcase_to_spaces("fooBar"), "foo Bar");
        assert_eq!(camelcase_to_spaces("FooBar"), "Foo Bar");
        assert_eq!(camelcase_to_spaces("AndroidVM"), "Android VM");
        assert_eq!(camelcase_to_spaces("RARFile"), "RAR File");
        assert_eq!(camelcase_to_spaces("ADruidsDuel"), "A Druids Duel");
    }

    #[test]
    fn camelcase_to_spaces_leaves_capitalization_alone() {
        assert_eq!(camelcase_to_spaces("foo"), "foo");
        assert_eq!(camelcase_to_spaces("Foo"), "Foo");
        assert_eq!(camelcase_to_spaces("fooBar"), "foo Bar");
        assert_eq!(camelcase_to_spaces("FooBar"), "Foo Bar");
        assert_eq!(camelcase_to_spaces("foo bar"), "foo bar");
        assert_eq!(camelcase_to_spaces("Foo Bar"), "Foo Bar");
    }

    #[test]
    fn camelcase_to_spaces_number_handling() {
        assert_eq!(camelcase_to_spaces("6LittleEggs"), "6 Little Eggs");
        assert_eq!(camelcase_to_spaces("6 Little Eggs"), "6 Little Eggs");
        assert_eq!(camelcase_to_spaces("the12chairs"), "the 12 chairs");
        assert_eq!(camelcase_to_spaces("The12Chairs"), "The 12 Chairs");
        assert_eq!(camelcase_to_spaces("The 12 Chairs"), "The 12 Chairs");
        assert_eq!(camelcase_to_spaces("1.5 Children"), "1.5 Children");
        assert_eq!(camelcase_to_spaces("The1.5Children"), "The 1.5 Children");
        assert_eq!(camelcase_to_spaces("the1.5children"), "the 1.5 children");
        assert_eq!(camelcase_to_spaces("Version1.1"), "Version 1.1");
        assert_eq!(camelcase_to_spaces("Version 1.1"), "Version 1.1");
        assert_eq!(camelcase_to_spaces("catch22"), "catch 22");
        assert_eq!(camelcase_to_spaces("Catch 22"), "Catch 22");
    }

    #[test]
    fn camelcase_to_spaces_doesnt_subdivide_numbers() {
        assert_eq!(camelcase_to_spaces("3.14"), "3.14");
        assert_eq!(camelcase_to_spaces("255"), "255");
        assert_eq!(camelcase_to_spaces("1000000"), "1000000");
        assert_eq!(camelcase_to_spaces("ut2003"), "ut 2003");
    }
}
