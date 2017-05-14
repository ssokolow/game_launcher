//!"""Routines for inferring a game's name"""
//!
//! TODO: Refactor the Python dependency out or make it optional

use std::borrow::Cow;
use std::ffi::OsStr;
use std::path::Path;

use regex::Regex;
use cpython::{PyModule, PyResult, Python};

// --== Constants and Statics ==--

use super::constants::{
    FNAME_WSPACE_RE, FNAME_WSPACE_NODASH_RE, INSTALLER_EXTS,
    PROGRAM_EXTS, SUBTITLE_START_RE, WHITESPACE_RE, WORD_BOUNDARY_CHARS
};

/// Used by `naming::camelcase_to_spaces` to insert spaces at word boundaries
const CAMELCASE_REPLACEMENT: &str = "${1}${3}${5}${7} ${2}${4}${6}${8}";
lazy_static! {
    /// Used by `naming::camelcase_to_spaces` to match word boundaries
    /// TODO: Move this to `super::constants` once `pub(restricted)` is stable
    static ref CAMELCASE_RE: Regex = Regex::new(r"(?x)
        # == Ampersand (definitely end) followed by anything not already whitespace ==
        #    ('Ampersand' or 'Small Ampersand', or 'Fullwidth Ampersand' or...
        #     'Heavy Ampersand Ornament')
        ([\x{26}\x{FE60}\x{FF06}\x{1F674}])
        #    (Something not 'Separator, Space')
        (\P{Zs})

        # == OR ==
        |

        # == Lower/titlecase (possible end) followed by upper/titlecase/number (possible start) ==
        #    ('Letter, Lowercase' or 'Letter, Titlecase', 'Ampersand' or 'Small Ampersand', or...
        #     'Fullwidth Ampersand' or 'Heavy Ampersand Ornament')
        ([\p{Ll}\p{Lt}])
        #    ('Letter, Uppercase' or 'Number, Decimal Digit' or 'Number, Letter' or...
        #     'Number, Other' or 'Ampersand' or 'Small Ampersand' or...
        #     'Fullwidth Ampersand' or 'Heavy Ampersand Ornament')
        ([\p{Lu}\p{Lt}\p{Nd}\p{Nl}\p{No}])

        # == OR ==
        |

        # == Number followed by an un-capitalized word ==
        #  ('Number, Decimal Digit' or 'Number, Letter' or 'Number, Other')
        ([\p{Nd}\p{Nl}\p{No}])
        #  ('Letter, Lowercase')
        (\p{Ll})

        #  == OR ==
        |

        # == Anything not whitespace, followed by ampersand or unambiguous beginnings of word ==
        #    (Something not 'Separator, Space')
        (\P{Zs})
        #    ('Letter, Titlecase' or ['Letter, Uppercase' followed by 'Letter, Lowercase'] or...
        #     'Ampersand' or 'Small Ampersand' or 'Fullwidth Ampersand' or ...
        #     'Heavy Ampersand Ornament')
        (\p{Lt} | \p{Lu}\p{Ll} | [\x{26}\x{FE60}\x{FF06}\x{1F674}])
        ").expect("compiled regex in string literal");
}

// --== Traits ==--

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

/// Insert spaces at word boundaries in a camelcase string.
pub fn camelcase_to_spaces(in_str: &str) -> String {
        let in_str2 = CAMELCASE_RE.replace_all(in_str, CAMELCASE_REPLACEMENT);
        CAMELCASE_RE.replace_all(&in_str2, CAMELCASE_REPLACEMENT).into_owned()
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
/// which may initially be using non-whitespace characters such as underscores or camelcasing.
pub fn normalize_whitespace(in_str: &str) -> Cow<str> {
    let underscore_count = in_str.count_char('_');
    let dash_count = in_str.count_char('-');

    // TODO: Come up with a way to count CamelCase transitions for use in this decision
    if underscore_count > 0 || dash_count > 0 {
        // TODO: Need to ignore `x86_64` when checking for underscores
        if underscore_count > dash_count {
            // Make sure things like "X-Com Collection" don't have their dashes converted
            FNAME_WSPACE_NODASH_RE.replace_all(in_str, " ")
        } else {
            // ...but also handle names using dashes as separators properly
            FNAME_WSPACE_RE.replace_all(in_str, " ")
        }
    } else {
        // Handle CamelCase cues
        Cow::Owned(camelcase_to_spaces(in_str))
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

/// `rust-cpython` API wrapper for `camelcase_to_spaces`
fn py_camelcase_to_spaces(_: Python, in_str: &str) -> PyResult<String> {
    Ok(camelcase_to_spaces(in_str))
}

/// `rust-cpython` API wrapper for `normalize_whitespace`
fn py_normalize_whitespace(_: Python, in_str: &str) -> PyResult<String> {
    Ok(normalize_whitespace(in_str).into_owned())
}

/// `rust-cpython` API wrapper for `titlecase_up`
fn py_titlecase_up(_: Python, in_str: &str) -> PyResult<String> { Ok(titlecase_up(in_str)) }

/// Called by parent modules to build and return the `rust-cpython` API wrapper.
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
    use super::{camelcase_to_spaces, titlecase_up};

    // -- camelcase_to_spaces --
    // TODO: Now that I have a better understanding of the state machine underlying CamelCase,
    //       I should refactor these tests to be more comprehensive and less duplication-heavy.

    #[test]
    fn camelcase_to_spaces_basic_function() {
        assert_eq!(camelcase_to_spaces("fooBar"), "foo Bar");
        assert_eq!(camelcase_to_spaces("FooBar"), "Foo Bar");
        assert_eq!(camelcase_to_spaces("AndroidVM"), "Android VM");
        assert_eq!(camelcase_to_spaces("RARFile"), "RAR File");
        assert_eq!(camelcase_to_spaces("ADruidsDuel"), "A Druids Duel");
        assert_eq!(camelcase_to_spaces("PickACard"), "Pick A Card");
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
    fn camelcase_to_spaces_ascii_number_handling() {
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
        assert_eq!(camelcase_to_spaces("1Two3"), "1 Two 3");
        assert_eq!(camelcase_to_spaces("One2Three"), "One 2 Three");
    }

    #[test]
    fn camelcase_to_spaces_basic_unicode_handling() {
        assert_eq!(camelcase_to_spaces("\u{1D7DE}ŁittléEggs"), "\u{1D7DE} Łittlé Eggs");
        assert_eq!(camelcase_to_spaces("ⅥŁittłeEggs"), "Ⅵ Łittłe Eggs");
        assert_eq!(camelcase_to_spaces("➅LittleEggs"), "➅ Little Eggs");
        assert_eq!(camelcase_to_spaces("\u{1D7DE} Łittlé Eggs"), "\u{1D7DE} Łittlé Eggs");
        assert_eq!(camelcase_to_spaces("Ⅵ Łittłe Eggs"), "Ⅵ Łittłe Eggs");
        assert_eq!(camelcase_to_spaces("➅ Little Eggs"), "➅ Little Eggs");
    }

    #[test]
    fn camelcase_to_spaces_titlecase_handling() {
        assert_eq!(camelcase_to_spaces("ǅ"), "ǅ");
        assert_eq!(camelcase_to_spaces("ǅxx"), "ǅxx");
        assert_eq!(camelcase_to_spaces("ǅX"), "ǅ X");
        assert_eq!(camelcase_to_spaces("Xǅ"), "X ǅ");
        assert_eq!(camelcase_to_spaces("Xxǅ"), "Xx ǅ");
        assert_eq!(camelcase_to_spaces("ǅXx"), "ǅ Xx");
        assert_eq!(camelcase_to_spaces("1ǅ2"), "1 ǅ 2");
    }

    #[test]
    fn camelcase_to_spaces_ampersand_handling() {
        assert_eq!(camelcase_to_spaces("TheKing&I"), "The King & I");
        assert_eq!(camelcase_to_spaces("TheKing﹠I"), "The King ﹠ I");
        assert_eq!(camelcase_to_spaces("TheKing＆I"), "The King ＆ I");
        assert_eq!(camelcase_to_spaces("TheKing\u{1F674}I"), "The King \u{1F674} I");
        assert_eq!(camelcase_to_spaces("A&b"), "A & b");
        assert_eq!(camelcase_to_spaces("A﹠b"), "A ﹠ b");
        assert_eq!(camelcase_to_spaces("A＆b"), "A ＆ b");
        assert_eq!(camelcase_to_spaces("A\u{1F674}b"), "A \u{1F674} b");
        assert_eq!(camelcase_to_spaces("1&2"), "1 & 2");
        assert_eq!(camelcase_to_spaces("ǅ&ǅ"), "ǅ & ǅ");
    }

    #[test]
    fn camelcase_to_spaces_doesnt_subdivide_numbers() {
        assert_eq!(camelcase_to_spaces("3.14"), "3.14");
        assert_eq!(camelcase_to_spaces("255"), "255");
        assert_eq!(camelcase_to_spaces("1000000"), "1000000");
        assert_eq!(camelcase_to_spaces("ut2003"), "ut 2003");
    }

    // -- titlecase_up --

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
        check_titlecase_up("foo-bar-baz-quux", "Foo-Bar-Baz-Quux");       // Lower with dashes
        check_titlecase_up("bit.trip.runner", "Bit.Trip.Runner");         // Lower with periods
        check_titlecase_up("green eggs and spam", "Green Eggs And Spam"); // Lower with spaces
        // TODO: Various mixes of separator characters
        // TODO: Various mixes of capitalization and separators
        check_titlecase_up("ScummVM", "ScummVM");                         // Unusual capitalization
        check_titlecase_up("FTL", "FTL");                                 // All-uppercase acronym
    }
}
