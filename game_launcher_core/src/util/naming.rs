//!"""Routines for inferring a game's name"""
//!
//! TODO: Refactor the Python dependency out or make it optional

use cpython::{PyModule, PyResult, PyUnicode, Python};

/// Characters which should trigger `titlecase_up` to uppercase the next one.
// NOTE: If titlecasing ever becomes a bottleneck or I feel like micro-optimizing just to amuse
// myself, I should be able to save some inner-loop iterations by reordering this based on the
// probability that these will be used as separators in a test corpus to maximize the ability of
// any() to short-circuit evaluate.
const WORD_BOUNDARY_CHARS: &str = ". _-";

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

/// rust-cpython API wrapper for `titlecase_up`
fn py_titlecase_up(_: Python, in_str: &str) -> PyResult<String> { Ok(titlecase_up(in_str)) }

/// TODO: Figure out how to get the `PyModule::new` and the return macro-ized
pub fn into_python_module(py: &Python) -> PyResult<PyModule> {
    let py = *py;
    let py_naming = PyModule::new(py, "naming")?;
    py_naming.add(py, "titlecase_up", py_fn!(py, py_titlecase_up(in_str: &str)))?;
    Ok(py_naming)
}

#[cfg(test)]
mod tests {
    use super::titlecase_up;

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
}
