//! Routines for parsing camelcase strings
//!

use std::mem::replace;
use regex::Regex;
use unicode_segmentation::{GraphemeIndices,UnicodeSegmentation};
use unicode_categories::UnicodeCategories;

// --== Constants and Statics ==--

lazy_static! {
    /// Used by `naming::camelcase_to_spaces` to match word boundaries
    ///
    /// TODO: Remove this once I've replaced the counting code
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

// --== Enums ==--

// TODO: Refresh my memory of which other traits I'm advised to derive on this.

/// Phase 1 intermediate representation used to separate classifying Unicode grapheme clusters from
/// defining state transitions between classes.
#[derive(Clone, Copy, Debug, PartialEq)]
enum CharType {
    /// No data has yet been processed
    Start,  // TODO: Is there any way to make this only usable as an initialization value?
    /// Uppercase
    Uppercase,
    /// Lowercase
    Lowercase,
    /// Character which combines an uppercase and lowercase character in the same glyph to allow
    /// round-trip compatibility with legacy encodings.
    Titlecase,
    /// One of the various types of ampersands Unicode defines
    Ampersand,
    /// One of the various types of apostrophes Unicode defines
    Apostrophe,
    /// A "numeric" character, as defined by Unicode
    Numeric,
    /// A decimal separator, thousands separator, or other "Number Separator"
    NumSep,
    /// A piece of punctuation which should not have a space after it, such as "(" or "#"
    StartPunct,
    /// A piece of punctuation which should not have a space before it, such as ")" or "%"
    EndPunct,
    /// A whitespace character
    Whitespace,
    /// Any character which does not fall into the other classes
    Other
}

/// Phase 2 intermediate representation used to separate defining state transitions between
/// character classes from actually processing the text to apply the defined transitions.
///
/// This acts as input to an algorithm which walks a `start_offset` and `end_offset` along the
/// input string, with `end_offset` always remaining one character behind the word's actual end
/// so that no fancy reverse-walking of UTF-8 is necessary to detect an <upper><lower> digraph
/// and then break before, rather than within it.
#[derive(Clone, Copy, Debug, PartialEq)]
enum CCaseAction {
    /// Just advance end_offset
    Literal,
    /// Emit accumulated word (if non-empty) and begin a new word starting with this grapheme
    StartWord,
    /// Shift a grapheme back out of the accumulator, then operate as in `StartWord`
    /// (Necessary to implement camelcase "<upper><lower>" handling in a single pass)
    AlreadyStartedWord,
    /// Emit accumulated word (if non-empty) and reset accumulator WITHOUT adding this grapheme
    /// (Necessary to skip whitespace characters)
    Skip,
}

// --== Classifier Functions ==--

/// Identify what role a given character plays in the string
fn classify_char(in_char: char) -> CharType {
    match in_char {
        // TODO: Adapt unicode.py from unicode-categories and auto-generate the "BIDI" categories
        // TODO: Find a crate to which I can delegate "BIDI" category membership checking
        //       (Membership checked at http://www.unicode.org/Public/UNIDATA/UnicodeData.txt)

        // Note: Keep this at the top in case things like U+00A0 make it into other matchers
        //       because of attributes like "BIDI: CS" classifications.
        x if x.is_whitespace() => CharType::Whitespace,

        // TODO: Is there any DB I can use to delegate "Ampersand" and "Apostrophe" definitisions?
        '\u{26}' | '\u{FE60}' | '\u{FF06}' | '\u{1F674}' => CharType::Ampersand,

        // Note: U+2019 (Right Single Quotation Mark)" is included here because FileFormat.info
        //       includes "U+2019 is preferred for apostrophe" in the "Comments" field.
        '\u{27}' | '\u{2019}' | '\u{FF07}' => CharType::Apostrophe,

        // Include "BIDI: Common Number Separators [CS]" as non-space-inducing
        // TODO: Add unit tests for all of these
        '\u{2c}' | '\u{2e}' | '\u{2f}' | '\u{3a}' | '\u{60c}' | '\u{2044}' | '\u{FE50}' |
                   '\u{FE52}' | '\u{FE55}' | '\u{FF0C}' | '\u{FF0E}' | '\u{FF0F}' | '\u{FF1A}' |

        // Include "BIDI: European Number Separator [ES]" as non-breaking based on test corpus
        // TODO: Add unit tests for all of these
                    '\u{2b}' | '\u{2d}' | '\u{207A}' | '\u{207B}' | '\u{208A}' | '\u{208B}' |
                    '\u{2212}' | '\u{FB29}' | '\u{FE62}' | '\u{FE63}' | '\u{FF0B}' | '\u{FF0D}'
            => CharType::NumSep,

        // Include "BIDI: European Number Terminator [ET]" as asymmetrically non-breaking based on
        // hard-coded rules like "$ breaks before" and "% breaks after".
        // TODO: Add unit tests for at least a large swathe of these
        // XXX: Try to build/intuit a corpus which would tell me whether it's feasible to make
        //      the "BIDI:ET" elements their own class which autodetects which side to break on
        //      based on surrounding characters. (Because that'd let me autogenerate it)
       '\u{23}' | '\u{24}' | '\u{a3}' | '\u{a4}' | '\u{a5}' | '\u{b1}' | '\u{20a0}' | '\u{20ac}' |
                  '\u{FE5F}' | '\u{FE69}' | '\u{FF03}' | '\u{FF04}' | '\u{ffe1}'
           => CharType::StartPunct,
       '\u{25}' | '\u{a2}' | '\u{b0}' | '\u{2030}' | '\u{2031}' | '\u{2032}' | '\u{2033}' |
                  '\u{2034}' | '\u{FE6A}' | '\u{ff05}' | '\u{ffe0}'
           => CharType::EndPunct,

        // Manually include a subset of "BIDI: Other Neutrals [ON]" as asymmetrically non-breaking
        // TODO: Which side should U+2E2E break on?
        '\u{A1}' | '\u{bf}' | '\u{2E18}' // Inverted question, exclamation, and interrobang
           => CharType::StartPunct,
        '\u{21}' | '\u{3b}' | '\u{3f}' | '\u{37e}' | '\u{2026}' | '\u{203c}' | '\u{203d}' |
                   '\u{2047}' | '\u{2048}' | '\u{2049}' | '\u{2762}' | '\u{FE54}' | '\u{FE56}' |
                   '\u{FE57}' | '\u{FF01}' | '\u{ff02}' | '\u{FF1B}' | '\u{FF1F}' | '\u{1F679}'
           => CharType::EndPunct,

        // Punctuation which should only trigger whitespace on one side
        x if x.is_punctuation_open() => CharType::StartPunct,
        x if x.is_punctuation_close() => CharType::EndPunct,

        // Basic numbers and letters
        x if x.is_numeric() => CharType::Numeric,
        x if x.is_uppercase() => CharType::Uppercase,
        x if x.is_lowercase() => CharType::Lowercase,
        x if x.is_letter_titlecase() => CharType::Titlecase,

        // Fall through to other types of symbols
        _ => CharType::Other
    }
}

/// Identify the action to take for a given transition between character roles
fn transition_to_action(old_type: CharType, new_type: CharType) -> CCaseAction {
    // FIXME: Silence `match_same_arms` lint. It could prompt someone to mess with precedence.
    match (old_type, new_type) {
        // Split instead of emitting whitespace (must have highest precedence)
        (_, CharType::Whitespace) => CCaseAction::Skip,

        // Always start a new word after whitespace, before titlecase, and before/after ampersands
        // TODO: More unit tests for the interaction between Ampersand and NumSep/etc.
        (CharType::Whitespace, _) |
        (_, CharType::Titlecase) |
        (CharType::Ampersand, _) | (_, CharType::Ampersand) => CCaseAction::StartWord,

        // Don't split before or after a "Number Separator" or apostrophe,
        // after opening punctuation, or before closing punctuation (eg. parens) unless overruled
        // by a higher-precedence rule.
        (CharType::NumSep, _) | (_, CharType::NumSep) |
        (CharType::Apostrophe, _) | (_, CharType::Apostrophe) |
        (CharType::StartPunct, _) | (_, CharType::EndPunct) => CCaseAction::Literal,

        // Retroactively locate the word-break if we find a lowercase after a titlecase/uppercase
        (CharType::Titlecase, CharType::Lowercase) |
        (CharType::Uppercase, CharType::Lowercase) => CCaseAction::AlreadyStartedWord,

        // If we reach this point and the character types differ, start a new word
        // TODO: I'll probably want to refine this with regards to CCaseAction::Other
        (x, y) if x != y => CCaseAction::StartWord,

        // ...otherwise, just pass it through verbatim
        _ => CCaseAction::Literal
    }
}

// --== Iterators ==--

/// External iterator for offsets of words as defined by camelcase rules.
pub struct WordOffsets<'a> {
    /// Grapheme iterator wrapping the source string
    in_iter: GraphemeIndices<'a>,
    /// Maximum valid end offset. Used for the final drain operation after the iterator runs out.
    in_len: usize,
    /// If true, don't split on existing runs of whitespace
    ///
    /// This is useful for counting camelcase transitions relative to other kinds of delimiters
    ///
    /// TODO: Actually implement this
    literal_ws: bool,

    // Used by the middle phase of each next() call
    /// The abstract type of the previous grapheme's base `char`. Used by `transition_to_action`.
    prev_type: CharType,

    // Used by the final phase of each next() call
    /// The start offset (in bytes) for the word currently being accumulated
    start_offset: usize,
    /// The previous value of `start_offset`. Used by `AlreadyStartedWord` to rewind split points.
    prev_offset: usize,
    /// Used to allow `CCaseAction::Skip` to not emit whitespace-only words
    skipping: bool,
}

impl<'a> WordOffsets<'a> {
    /// Helper to deduplicate the code involved in advancing to the next word in the iterator
    fn _next_word(&mut self, end_offset: usize, skip: bool) -> Option<(usize, usize)> {
        // We have to update our state variables no matter what the outcome, so do this first.
        let skipping = replace(&mut self.skipping, skip);
        let start_offset = replace(&mut self.start_offset, end_offset);

        // If our previous "word" is non-empty and we're not skipping it, return it
        if start_offset < end_offset && !skipping {
            Some((start_offset, end_offset))
        } else {
            None
        }
    }
}
impl<'a> Iterator for WordOffsets<'a> {
    type Item = (usize, usize);

    fn next(&mut self) -> Option<(usize, usize)> {
        // Get the next grapheme cluster and its byte index
        // Note: Using `while let` instead of `for` is necessary to avoid a borrow conflict
        #[allow(while_let_on_iterator)]
        while let Some((byte_offset, grapheme)) = self.in_iter.next() {
            // Extract the base `char` so `classify_char` can call things like `is_uppercase`
            let base = grapheme.chars().nth(0).expect("non-empty grapheme cluster");

            // Identify character types and map transitions between them to actions
            let curr_type = classify_char(base);
            let curr_action = transition_to_action(replace(&mut self.prev_type, curr_type),
                                                   curr_type);

            // Actually apply the action to the iterator's state and, if the action returns an
            // accumulated word, return it.
            // TODO: Consider using an enum for the skip=true/false
            let prev_offset = replace(&mut self.prev_offset, byte_offset);
            if let Some(pair) = match curr_action {
                CCaseAction::Literal => { None }, // The grapheme iterator will advance it for us
                CCaseAction::Skip => { self._next_word(byte_offset, true) },
                CCaseAction::StartWord => { self._next_word(byte_offset, false) },
                CCaseAction::AlreadyStartedWord => { self._next_word(prev_offset, false) },
            } {
                return Some(pair);
            }
        }

        // Drain the remaining graphemes into a final word, if present
        let in_len = self.in_len;
        self._next_word(in_len, true)
    }
}


/// External iterator for words in a string as defined by camelcase rules.
///
/// Note: This API should be considered unstable as I have plans to rewrite it once
/// `impl Iterator<Item=&str>` is stabilized.
pub struct Words<'a> {
    /// Source string from which slices will be returned
    in_str: &'a str,
    /// Offset iterator wrapping the source string
    in_iter: WordOffsets<'a>,
}
impl<'a> Iterator for Words<'a> {
    type Item = &'a str;

    fn next(&mut self) -> Option<&'a str> {
        #[allow(indexing_slicing)]
        match self.in_iter.next() {
            Some((start, end)) => Some(&self.in_str[start..end]),
            None => None
        }
    }
}

/// Extension trait to add camelcase-based wordwise iterators to &str
pub trait CamelCaseIterators {
    /// Returns an iterator over the `(start_offset, end_offset)` tuples defining words within the
    /// string, as separated by camelcase rules.
    ///
    /// TODO: If literal_whitespace is `true`, only split on camelcase boundaries, passing
    /// whitespace through literally. (Useful for stats-gathering)
    fn camelcase_offsets(&self, literal_whitespace: bool) -> WordOffsets;

    /// Returns an iterator over the words of the string, separated by camelcase rules.
    ///
    /// TODO: If literal_whitespace is `true`, only split on camelcase boundaries, passing
    /// whitespace through literally. (Useful for stats-gathering)
    fn camelcase_words(&self, literal_whitespace: bool) -> Words;
}

impl CamelCaseIterators for str {
    fn camelcase_offsets(&self, literal_whitespace: bool) -> WordOffsets {
    WordOffsets {
        in_iter: self.grapheme_indices(true),
        in_len: self.len(),
        literal_ws: literal_whitespace,
        // TODO: Implement literal_ws and unit test it

        prev_type: CharType::Start,

        skipping: false,
        start_offset: 0,
        prev_offset: 0,
    }
}

    fn camelcase_words(&self, literal_whitespace: bool) -> Words {
        Words {
            in_str: self,
            in_iter: self.camelcase_offsets(literal_whitespace),
        }
    }
}

// --== Loose Functions ==--

// TODO: Update this docstring once I've tested against the additional 850+ filenames still to be
// added to the corpus.
/// Insert spaces at word boundaries in a camelcase string.
///
/// This implementation differs from the form of camelcase typically used for function names in
/// that it will insert spaces between words and numbers.
/// (ie. "Thing Part 1" rather than "Thing Part1")
///
/// This decision was made based on the following observations taken from a corpus of over 800
/// real-world computer game directory and installer/archive file names:
///
/// 1. It produces a more accurate translation to the intended titles.
/// 2. It is in accordance with how, unlike method names, `snake_case` in video game filenames
///    separates numbers from the words they follow.
///
/// The test data in question can be found in the `filename_to_name_data.json` file used by the
/// top-level integration tests for this project.
pub fn camelcase_to_spaces(in_str: &str) -> String {
    // TODO: Depend on itertools and use join() directly on the iterator instead
    in_str.camelcase_words(false).collect::<Vec<_>>().join(" ")
}

// TODO: Replace everything below except tests with the Iterator-ified version of the code above.
use super::ConvenientCharCount;
const CAMELCASE_COUNT_REPLACEMENT: &str = "${1}${3}${5}${7}\0${2}${4}${6}${8}";

/// Return the number of camelcase word boundaries in a string.
///
/// See `camelcase_to_spaces` for further details.
///
/// **NOTE:** This is a temporary implementation to allow the dependent code to be refined. It will
///     be replaced by a properly efficient, non-regex-based solution.
pub fn camelcase_count(in_str: &str) -> usize {
        // TODO: Unit test, then replace with .camelcase_words(false).count()
        let in_str2 = CAMELCASE_RE.replace_all(in_str, CAMELCASE_COUNT_REPLACEMENT);
        CAMELCASE_RE.replace_all(&in_str2, CAMELCASE_COUNT_REPLACEMENT).count_char('\0')
}

// --== Tests ==--

#[cfg(test)]
mod tests {
    use super::camelcase_to_spaces;

    /// Helper to deduplicate verifying that camelcase_to_spaces output is stable
    fn check_camelcase_to_spaces(input: &str, expected: &str) {
        let result = camelcase_to_spaces(input);
        assert_eq!(result, expected, "(with input {:?})", input);
        assert_eq!(camelcase_to_spaces(&result), result,
                   "camelcase_to_spaces should be a no-op when re-run on its own output");
    }

    #[test]
    fn camelcase_to_spaces_basic_function() {
        check_camelcase_to_spaces("fooBar", "foo Bar");
        check_camelcase_to_spaces("FooBar", "Foo Bar");
        check_camelcase_to_spaces("AndroidVM", "Android VM");
        check_camelcase_to_spaces("RARFile", "RAR File");
        check_camelcase_to_spaces("ADruidsDuel", "A Druids Duel");
        check_camelcase_to_spaces("PickACard", "Pick A Card");
        check_camelcase_to_spaces("AxelF", "Axel F");
    }

    #[test]
    fn camelcase_to_spaces_leaves_capitalization_alone() {
        check_camelcase_to_spaces("foo", "foo");
        check_camelcase_to_spaces("Foo", "Foo");
        check_camelcase_to_spaces("fooBar", "foo Bar");
        check_camelcase_to_spaces("FooBar", "Foo Bar");
        check_camelcase_to_spaces("foo bar", "foo bar");
        check_camelcase_to_spaces("Foo Bar", "Foo Bar");
    }

    #[test]
    fn camelcase_to_spaces_ascii_number_handling() {
        check_camelcase_to_spaces("6LittleEggs", "6 Little Eggs");
        check_camelcase_to_spaces("6 Little Eggs", "6 Little Eggs");
        check_camelcase_to_spaces("the12chairs", "the 12 chairs");
        check_camelcase_to_spaces("The12Chairs", "The 12 Chairs");
        check_camelcase_to_spaces("The 12 Chairs", "The 12 Chairs");
        check_camelcase_to_spaces("1.5 Children", "1.5 Children");
        check_camelcase_to_spaces("The1.5Children", "The 1.5 Children");
        check_camelcase_to_spaces("the1.5children", "the 1.5 children");
        check_camelcase_to_spaces("Version1.1", "Version 1.1");
        check_camelcase_to_spaces("Version 1.1", "Version 1.1");
        check_camelcase_to_spaces("catch22", "catch 22");
        check_camelcase_to_spaces("Catch 22", "Catch 22");
        check_camelcase_to_spaces("1Two3", "1 Two 3");
        check_camelcase_to_spaces("One2Three", "One 2 Three");
        check_camelcase_to_spaces("ONE2", "ONE 2");
        check_camelcase_to_spaces("ONE2THREE", "ONE 2 THREE");
    }

    #[test]
    fn camelcase_to_spaces_basic_unicode_handling() {
        check_camelcase_to_spaces("\u{1D7DE}ŁittléEggs", "\u{1D7DE} Łittlé Eggs");
        check_camelcase_to_spaces("ⅥŁittłeEggs", "Ⅵ Łittłe Eggs");
        check_camelcase_to_spaces("➅LittleEggs", "➅ Little Eggs");
        check_camelcase_to_spaces("\u{1D7DE} Łittlé Eggs", "\u{1D7DE} Łittlé Eggs");
        check_camelcase_to_spaces("Ⅵ Łittłe Eggs", "Ⅵ Łittłe Eggs");
        check_camelcase_to_spaces("➅ Little Eggs", "➅ Little Eggs");
    }

    #[test]
    fn camelcase_to_spaces_titlecase_handling() {
        check_camelcase_to_spaces("ǅ", "ǅ");
        check_camelcase_to_spaces("ǅxx", "ǅxx");
        check_camelcase_to_spaces("ǅX", "ǅ X");
        check_camelcase_to_spaces("Xǅ", "X ǅ");
        check_camelcase_to_spaces("Xxǅ", "Xx ǅ");
        check_camelcase_to_spaces("ǅXx", "ǅ Xx");
        check_camelcase_to_spaces("1ǅ2", "1 ǅ 2");
    }

    #[test]
    fn camelcase_to_spaces_ampersand_handling() {
        check_camelcase_to_spaces("TheKing&I", "The King & I");
        check_camelcase_to_spaces("TheKing﹠I", "The King ﹠ I");
        check_camelcase_to_spaces("TheKing＆I", "The King ＆ I");
        check_camelcase_to_spaces("TheKing\u{1F674}I", "The King \u{1F674} I");
        check_camelcase_to_spaces("A&b", "A & b");
        check_camelcase_to_spaces("A﹠b", "A ﹠ b");
        check_camelcase_to_spaces("A＆b", "A ＆ b");
        check_camelcase_to_spaces("A\u{1F674}b", "A \u{1F674} b");
        check_camelcase_to_spaces("1&2", "1 & 2");
        check_camelcase_to_spaces("ǅ&ǅ", "ǅ & ǅ");
        check_camelcase_to_spaces("Forsooth&'tisTrue", "Forsooth & 'tis True");
    }

    #[test]
    fn camelcase_to_spaces_apostrophe_handling() {
        check_camelcase_to_spaces("Don'tMove", "Don't Move");
        check_camelcase_to_spaces("Don\u{2019}tMove", "Don\u{2019}t Move");
        check_camelcase_to_spaces("Don\u{FF07}tMove", "Don\u{FF07}t Move");
        check_camelcase_to_spaces("It's my kids' kids'", "It's my kids' kids'");
        check_camelcase_to_spaces("it\u{2019}s my kids\u{2019} kids\u{2019}",
                                  "it\u{2019}s my kids\u{2019} kids\u{2019}");
        check_camelcase_to_spaces("it\u{FF07}s my kids\u{FF07} kids\u{FF07}",
                                  "it\u{FF07}s my kids\u{FF07} kids\u{FF07}");
    }

    #[test]
    fn camelcase_to_spaces_open_close_handling() {
        check_camelcase_to_spaces("Who?Him!Really?Yeah!", "Who? Him! Really? Yeah!");
        check_camelcase_to_spaces("100%Juice", "100% Juice");
        check_camelcase_to_spaces("WeAre#1", "We Are #1");
        check_camelcase_to_spaces("ShadowWarrior(2013)", "Shadow Warrior (2013)");
        check_camelcase_to_spaces("SallyFace[linux]", "Sally Face [linux]");
        check_camelcase_to_spaces("SallyFace[Linux]", "Sally Face [Linux]");
        check_camelcase_to_spaces("TestyFoo{Bar}Baz", "Testy Foo {Bar} Baz");
        check_camelcase_to_spaces("ShadowWarrior\u{FF08}2013\u{FF09}",
                                  "Shadow Warrior \u{FF08}2013\u{FF09}");
        check_camelcase_to_spaces("[ǅxx]", "[ǅxx]");
        check_camelcase_to_spaces(" [ǅxx] ", "[ǅxx]");
    }

    #[test]
    fn camelcase_to_spaces_doesnt_subdivide_numbers() {
        check_camelcase_to_spaces("3.14", "3.14");
        check_camelcase_to_spaces("255", "255");
        check_camelcase_to_spaces("1000000", "1000000");
        check_camelcase_to_spaces("ut2003", "ut 2003");
    }

    #[test]
    fn camelcase_to_spaces_unicode_segmentation() {
        /// Zalgo text generated using http://eeemo.net/
        check_camelcase_to_spaces("f̴͘͟͜ǫ̴̸̧͘ó̵̢̢͏B̴̨͠á̵̸͡r̶̵͢͠", "f̴͘͟͜ǫ̴̸̧͘ó̵̢̢͏ B̴̨͠á̵̸͡r̶̵͢͠");
        check_camelcase_to_spaces("Ŕ̀̕͟͞À̸̛͞͞Ŕ̨̕F̕͜͟͠í̵͜l҉̨e̶̵", "Ŕ̀̕͟͞À̸̛͞͞Ŕ̨̕ F̕͜͟͠í̵͜l҉̨e̶̵");
        check_camelcase_to_spaces("P̕͟͠i҉͢c̨̨͞͡ḱ̸̕Ą̸Ç͘͜a͘͟r̀͟͢҉̵d̕͜", "P̕͟͠i҉͢c̨̨͞͡ḱ̸̕ Ą̸ Ç͘͜a͘͟r̀͟͢҉̵d̕͜");
        check_camelcase_to_spaces("6̢L̢͏͏͠i̷̛͜t̷̕t̷͟ļ͟͢ȩ̨̕̕È̷̸g̵̷̨͢͡g̷s͟͞", "6̢ L̢͏͏͠i̷̛͜t̷̕t̷͟ļ͟͢ȩ̨̕̕ È̷̸g̵̷̨͢͡g̷s͟͞");
        check_camelcase_to_spaces("t̶̨͞h̨͝͝e̡͟͢1̴̧̀͘͟2͘͘c̷̴̢͘h̶̴̢͢à͘͏i̡̛r͜s̷͏", "t̶̨͞h̨͝͝e̡͟͢ 1̴̧̀͘͟2͘͘ c̷̴̢͘h̶̴̢͢à͘͏i̡̛r͜s̷͏");
        check_camelcase_to_spaces("T̶͡ḩ̷̷͟ȩ̛́͘͡1̵̨̕͢2̕͝C̸̡͞͏͟h̴̵̀a҉͜͢i̵̸̡̕ŗ̴͢s̴͏͘͡", "T̶͡ḩ̷̷͟ȩ̛́͘͡ 1̵̨̕͢2̕͝ C̸̡͞͏͟h̴̵̀a҉͜͢i̵̸̡̕ŗ̴͢s̴͏͘͡");
        check_camelcase_to_spaces("T͠҉̸̷h̀͡e̡̨͝͠1̴́͏.͏̨́͠͝5̨́̕C̷͜͏͠h̢̧͝ì̡̢̕l̸͞͡d̵̕͢͡ŕ̶͘͡͞e͜͝n̨҉̕", "T͠҉̸̷h̀͡e̡̨͝͠ 1̴́͏.͏̨́͠͝5̨́̕ C̷͜͏͠h̢̧͝ì̡̢̕l̸͞͡d̵̕͢͡ŕ̶͘͡͞e͜͝n̨҉̕");
        check_camelcase_to_spaces("t̡̛͟h͏҉҉́è͝͠1̢̕͟͟.̶̛5̶͜ć̀ḩ̶̸̕͜i̸̕͢l̢͡͝͝͏d͘͟r̨͢e̢҉̵͞͠n̛", "t̡̛͟h͏҉҉́è͝͠ 1̢̕͟͟.̶̛5̶͜ ć̀ḩ̶̸̕͜i̸̕͢l̢͡͝͝͏d͘͟r̨͢e̢҉̵͞͠n̛");
        check_camelcase_to_spaces("V̶͞e̡͜͟͠r̢͟s̀͏̧̢̕i̸̧͞͠o̷̸̧n̡͞1̧̀͘͟͞.̸̕1́͞҉", "V̶͞e̡͜͟͠r̢͟s̀͏̧̢̕i̸̧͞͠o̷̸̧n̡͞ 1̧̀͘͟͞.̸̕1́͞҉");
        check_camelcase_to_spaces("A̴&͏̵̛b͝", "A̴ &͏̵̛ b͝");
        check_camelcase_to_spaces("u̢҉͡t̸̷̛2̶͏͡0́̕҉̶0̡͞͡3̴̷͟", "u̢҉͡t̸̷̛ 2̶͏͡0́̕҉̶0̡͞͡3̴̷͟");
    }
}
