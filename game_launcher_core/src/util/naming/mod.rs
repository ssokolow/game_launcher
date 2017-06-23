//! Routines for inferring a game's title from its file/directory name.
//!
//! (Used by other modules as a fallback when attempts to extract metadata fail to produce
//! a title.)
//!
//! **TODO:** Refactor the Python dependency out or make it optional

use std::borrow::Cow;
use std::ffi::OsStr;
use std::path::Path;

use cpython::{PyModule, PyResult, Python};

// --== Constants and Statics ==--

use super::constants::{
    FNAME_WSPACE_RE, FNAME_WSPACE_NODASH_RE,
    PROGRAM_EXTS, SUBTITLE_START_RE, WHITESPACE_RE, WORD_BOUNDARY_CHARS
};

mod camelcase;

pub use self::camelcase::CamelCaseIterators;

// --== Traits ==--

// TODO: Decide whether and how to expose this functionality.

/// Boilerplate to make it clean to count occurrences of a char
/// (The trait name is considered a private implementation detail)
trait ConvenientCharCount {
    /// Count the number of occurrences of `needle` in the string
    fn count_char(&self, needle: char) -> usize;
}
impl ConvenientCharCount for str {
    fn count_char(&self, needle: char) -> usize {
        self.chars().filter(|x| x == &needle).count()
    }
}

// --== Loose Functions ==--

// TODO: Write a function which generates sorting keys like "Boy And His Blob, A" from titles.

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

/// Heuristically transform a path or file/directory name to produce a high-accuracy guess at the
/// title which the path's final component it is intended to represent.
///
/// Within the limits of what is attainable without resorting to out-of-band information (eg.
/// splitting "abirdstory" would require an external word list), this function currently produces
/// an "attainably perfect" result for over 90% of the test strings in the
/// `filename_to_name_data.json` corpus used by the test suite.
///
/// (Accuracy will continue to improve as many of the mis-guesses are either due to known
///  shortcomings in the algorithm which have planned solutions or due to plain-and-simple
///  rule-precedence bugs that have yet to be shaken out by the in-progress refactoring.)
pub fn filename_to_name<P: AsRef<Path> + ?Sized>(path: &P) -> Option<String> {
    let name_in = _filename_extensionless(path);

    // TODO: Refactor this function for simplicity and early return
    // TODO: Group the algorithm into labelled phases

    // Throw out all "words" starting with the first thing identified as a version number.
    // TODO: Replace the map()'s innards with a successor to fname_ver_re
    // TODO: What's the simplest way to give the first element a pass from filtering?
    // TODO: Verify that using `.map() -> None` short-circuits iteration.
    //       (And is there a more idiomatic way?)
    // TODO: Figure out how to filter a "v" conditional on the next "word" being a number
    //       (ie. backtracking)
    //    name = fname_ver_re.sub('', fname)
    let name_in = name_in
        .split_whitespace()
        .map(|x| x)
        .collect::<Vec<_>>().join(" ");

    // TODO: Maybe I should convert whitespace cues first, then filter out version information in
    //      a wordwise manner.
    let name = normalize_whitespace(&name_in);

    // Assume that a number followed by whitespace and more text marks the beginning of a subtitle
    // and add a colon and normalized space
    let name = SUBTITLE_START_RE.replace_all(&name, "${1}: ${2}");

    // Titlecase... but only in the lower->upper direction so things like "FTL" remain
    let name_in = titlecase_up(&name);

    // Ensure that numbers are preceded by a space (Anticipate two inserted spaces at most)
    // TODO: Check my guess of "2" against my test corpus
    let mut name = String::with_capacity(name_in.len().saturating_add(2));
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
    //    name = re.sub('|'.join(WHITESPACE_OVERRIDES), _apply_ws_overrides, name)

    // Normalize whitespace which may be left over
    name = WHITESPACE_RE.replace_all(&name, " ").trim().to_string();

    // Return `None` instead of an empty string to make it clear that this can fail.
    // (Whitespace and Unicode replacement characters are excluded from the count)
    match name.chars().filter(|x| !(*x == '\u{FFFD}' || x.is_whitespace())).count() {
        0 => None,
        _ => Some(name)
    }
}

enum SeparatorType {
    CamelCase,
    Dash,
    Period,
    Plus,
    Space,
    Underscore,
}

/// Helper for `filename_to_name` to heuristically normalize word-breaks in filenames
/// which may initially be using non-whitespace characters such as underscores or camelcasing.
///
/// **NOTE:** This is currently being refactored for accuracy and maintainability based on lessons
/// learned from experimenting with real-world examples.
///
/// My suspicion is that the best algorithm to handle whitespace inference will be:
///
/// 1. Receive a string that's had any file extensions already stripped
/// 2. Collapse runs of \w into a single space
/// 3. Count the number of spaces, underscores, dashes, periods, pluses, %20s, and camelcase word
///    boundaries.
/// 4. Pick whichever two are most common as the word delimiters.
///
/// (Probably in two passes, since I suspect it'll be easiest to reliably match certain kinds of
/// tokens while in intermediate form.)
///
///
/// Another possible approach would be to take the order in which the delimiters appear in the
/// string, since I've noticed that filenames which use two layers of delimiters tend to use them
/// in a hierarchical form, such as `NameOfGame_linuxBuild_1.0.zip`
pub fn normalize_whitespace(in_str: &str) -> Cow<str> {
    // TODO: I think I'm going to have to constrain `CamelCase` and `Period` to the second pass.
    //let counts = [
    //    (SeparatorType::CamelCase, in_str.camelcase_offsets(true).count()),
    //    (SeparatorType::Dash, in_str.count_char('-')),
    //    //(SeparatorType::Period, in_str.count_char('.')), // FIXME: Don't get fooled by versions
    //    (SeparatorType::Plus, in_str.count_char('+')),  // TODO: ignore ++ as in C++/N++
    //    (SeparatorType::Space, in_str.count_char(' ')),  // TODO: Collapse whitespace first
    //    (SeparatorType::Underscore, in_str.count_char('_'))
    //    // TODO: Decide on an ordering so that "last wins" precedence is useful for equal counts.
    //];

    //return match counts.iter().max_by_key(|x| x.1).expect("max_by_key() returned None for \
    //        an array with a length known at compile time").0 {
    //    SeparatorType::Underscore => Cow::Owned(in_str.replace("_", " ")),
    //    SeparatorType::Dash => Cow::Owned(in_str.replace("-", " ")),
    //    SeparatorType::Plus => Cow::Owned(in_str.replace("+", " ")),  // TODO: ignore ++ as in C++/N++
    //    _ => Cow::Owned(in_str.camelcase_words(false).collect::<Vec<_>>().join(" "))
    //};

    let underscore_count = in_str.count_char('_');
    let dash_count = in_str.count_char('-');
    // TODO: <Dabo> storing a list of (count, closure) really doesn't seem that bad to me - though I'd probably do a SeparationType enum rather than a closure, then just get the max count with list.iter().max_by_key()

    // TODO: Come up with a way to count CamelCase transitions for use in this decision
    if underscore_count > 0 || dash_count > 0 {
        if underscore_count > dash_count {
            // Make sure things like "X-Com Collection" don't have their dashes converted
            FNAME_WSPACE_NODASH_RE.replace_all(in_str, " ")
        } else {
            // ...but also handle names using dashes as separators properly
            FNAME_WSPACE_RE.replace_all(in_str, " ")
        }
    } else {
        // Handle CamelCase cues
        Cow::Owned(in_str.camelcase_words(false).collect::<Vec<_>>().join(" "))

        // TODO: If the string is fully lowercase before any case normalization occurs, or there
        // are no spaces, and + characters occur in more than two disjoint locations
        // (ie. not CaveStory+ or N++ or DROD 1+2+3), try treating + as a token delimiter.
    }
}

/// Return a titlecased copy of the input with the following two modifications to the algorithm:
///
/// 1. Never perform upper->lowercase conversion in order to preserve acronyms like RPG.
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

/// `rust-cpython` API wrapper for `CamelCaseIterators::camelcase_words`
/// TODO: Finish factoring out the "join"
fn py_camelcase_to_spaces(_: Python, in_str: &str) -> PyResult<String> {
    Ok(in_str.camelcase_words(false).collect::<Vec<_>>().join(" "))
}

/// `rust-cpython` API wrapper for `normalize_whitespace`
fn py_normalize_whitespace(_: Python, in_str: &str) -> PyResult<String> {
    Ok(normalize_whitespace(in_str).into_owned())
}

/// `rust-cpython` API wrapper for `titlecase_up`
fn py_titlecase_up(_: Python, in_str: &str) -> PyResult<String> { Ok(titlecase_up(in_str)) }

/// Called by parent modules to build and return the `rust-cpython` API wrapper.
///
/// TODO: Figure out how to get the `PyModule::new` and the return macro-ized
pub fn into_python_module(py: &Python) -> PyResult<PyModule> {
    let py = *py;
    let py_naming = PyModule::new(py, "naming")?;
    py_naming.add(py, "camelcase_to_spaces", py_fn!(py, py_camelcase_to_spaces(in_str: &str)))?;
    py_naming.add(py, "normalize_whitespace", py_fn!(py, py_normalize_whitespace(in_str: &str)))?;
    py_naming.add(py, "titlecase_up", py_fn!(py, py_titlecase_up(in_str: &str)))?;
    Ok(py_naming)
}

// --== Tests ==--

#[cfg(test)]
mod tests {
    use super::titlecase_up;

    // -- titlecase_up --

    fn check_titlecase_up(input: &str, expected: &str) {
        let result = titlecase_up(input);
        assert_eq!(result, expected, "(with input {:?})", input);
        assert_eq!(titlecase_up(&result), result,
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
        check_titlecase_up("foo-bar-baz-quux", "Foo-Bar-Baz-Quux");       // Lower with dashes
        check_titlecase_up("bit.trip.runner", "Bit.Trip.Runner");         // Lower with periods
        check_titlecase_up("green eggs and spam", "Green Eggs And Spam"); // Lower with spaces
        // TODO: Various mixes of separator characters
        // TODO: Various mixes of capitalization and separators
        check_titlecase_up("ScummVM", "ScummVM");                         // Unusual capitalization
        check_titlecase_up("FTL", "FTL");                                 // All-uppercase acronym
    }
}
