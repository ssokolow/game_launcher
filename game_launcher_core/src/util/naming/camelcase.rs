//! Routines for parsing camelcase strings
//!

use std::mem::replace;
use unicode_segmentation::{GraphemeIndices,UnicodeSegmentation};
use unicode_categories::UnicodeCategories;

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
    /// Like `Literal`, but prevent the following character from being the split point for a new
    /// word (Used to suppress AlreadyStartedWord in cases like "[Hello]")
    Suppress,
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

        // TODO: Is there any DB I can use to delegate "Ampersand" and "Apostrophe" definitions?
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
        // TODO: Add characters from these "see also" lists:
        //       - http://www.fileformat.info/info/unicode/char/003c/index.htm
        //       - http://www.fileformat.info/info/unicode/char/003e/index.htm
        //       - http://www.fileformat.info/info/unicode/char/search.htm?q=%22&preview=entity
        // TODO: Add unit tests for at least a large swathe of these
        // XXX: Is there an attribute that identifies asymmetric quote characters?
        // XXX: Try to build/intuit a corpus which would tell me whether it's feasible to make
        //      the "BIDI:ET" elements their own class which autodetects which side to break on
        //      based on surrounding characters. (Because that'd let me autogenerate it)
       '\u{23}' | '\u{24}' | '\u{a3}' | '\u{a4}' | '\u{a5}' | '\u{ab}' | '\u{b1}' | '\u{20a0}' |
                  '\u{20ac}' | '\u{FE5F}' | '\u{FE69}' | '\u{FF03}' | '\u{FF04}' | '\u{ffe1}'
           => CharType::StartPunct,
       '\u{25}' | '\u{a2}' | '\u{b0}' | '\u{bb}' | '\u{2030}' | '\u{2031}' | '\u{2032}' |
                  '\u{2033}' | '\u{2034}' | '\u{FE6A}' | '\u{ff05}' | '\u{ffe0}'
           => CharType::EndPunct,

        // Manually include a subset of "BIDI: Other Neutrals [ON]" as asymmetrically non-breaking
        // TODO: Which side should U+2E2E break on?
        '\u{3c}' | '\u{A1}' | '\u{bf}' | '\u{2E18}' | '\u{fe64}' | '\u{ff1c}'
           => CharType::StartPunct,
        '\u{21}' | '\u{3b}' | '\u{3e}' | '\u{3f}' | '\u{37e}' | '\u{2026}' | '\u{203c}' |
                   '\u{203d}' | '\u{2047}' | '\u{2048}' | '\u{2049}' | '\u{2762}' | '\u{FE54}' |
                   '\u{FE56}' | '\u{FE57}' | '\u{fe65}' | '\u{FF01}' | '\u{ff02}' | '\u{FF1B}' |
                   '\u{FF1E}' | '\u{FF1F}' | '\u{1F679}'
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

        // Block AlreadyStartedWord in situations like "(Hello"
        (CharType::StartPunct, _) => CCaseAction::Suppress,

        // Always start a new word after whitespace, before titlecase, and before/after ampersands
        // TODO: More unit tests for the interaction between Ampersand and NumSep/etc.
        (CharType::Whitespace, _) |
        (_, CharType::Titlecase) |
        (CharType::Ampersand, _) | (_, CharType::Ampersand) => CCaseAction::StartWord,

        // Don't split before or after a "Number Separator" or apostrophe
        // or before closing punctuation (eg. parens) unless overruled by a higher-precedence rule.
        (CharType::NumSep, _) | (_, CharType::NumSep) |
        (CharType::Apostrophe, _) | (_, CharType::Apostrophe) |
        (_, CharType::EndPunct) => CCaseAction::Literal,

        // Retroactively locate the word-break if we find a lowercase after a titlecase/uppercase
        // FIXME: An additional CCaseAction needs to be defined so StartPunct can overrule this
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
    /// If true, split only on CamelCase transitions, passing other delimiters through as literals
    ///
    /// This is useful for counting camelcase transitions relative to other kinds of delimiters
    ///
    /// TODO: Actually implement this
    strict: bool,

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
    /// Used to allow `CCaseAction::Suppress` to block `AlreadyStartedWord`
    suppress: usize,
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
                CCaseAction::Skip => { self._next_word(byte_offset, true) },
                CCaseAction::StartWord if self.suppress != byte_offset => {
                    self._next_word(byte_offset, false) },
                CCaseAction::AlreadyStartedWord if self.suppress != prev_offset => {
                    self._next_word(prev_offset, false)
                },
                CCaseAction::Suppress => { self.suppress = byte_offset; None },
                _ => { None }, // Use Literal as the fallback behaviour

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
/// NOTE: This API should be considered unstable as I have plans to rewrite it once
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
    ///
    /// TODO: If strict `true`, only split on camelcase boundaries, passing other delimiters
    /// through literally. (Useful for stats gathering)
    fn camelcase_offsets(&self, strict: bool) -> WordOffsets;

    /// Returns an iterator over the words of the string, separated by camelcase rules.
    ///
    /// See `camelcase_offsets` for details.
    ///
    /// TODO: If strict `true`, only split on camelcase boundaries, passing other delimiters
    /// through literally. (Useful for stats gathering)
    fn camelcase_words(&self, strict: bool) -> Words;
}

impl CamelCaseIterators for str {
    // TODO: Once I'm set up for benchmarking, check whether I should copy the tactic
    // unicode_segmentation applies involving #[inline] annotations

    fn camelcase_offsets(&self, strict: bool) -> WordOffsets {
    if strict { unimplemented!(); }

    WordOffsets {
        in_iter: self.grapheme_indices(true),
        in_len: self.len(),
        strict,
        // TODO: Implement strict and unit test it

        prev_type: CharType::Start,

        start_offset: 0,
        prev_offset: 0,

        // Use the maximum possible value for `suppress` to mean "unset" because the whole point is
        // to affect the behaviour of suppress+1... which means this can't collide with anything.
        suppress: usize::max_value(), // Use the maximum value for "unset" since
        skipping: false,
    }
}

    fn camelcase_words(&self, strict: bool) -> Words {
        Words {
            in_str: self,
            in_iter: self.camelcase_offsets(strict),
        }
    }
}

// --== Tests ==--

#[cfg(test)]
mod tests {
    use super::CamelCaseIterators;

    /// Helper to deduplicate verifying that CamelCaseIterators output is stable
    fn check_camelcase_words(input: &str, expected: &[&str]) {
        let result = input.camelcase_words(false).collect::<Vec<_>>();
        assert_eq!(result, expected, "(with input {:?})", input);

        let result_j = result.join(" ");
        assert_eq!(result_j.camelcase_words(false).collect::<Vec<_>>(), result,
                   "camelcase_words should be a no-op when re-run on its own output");

        assert_eq!(input.camelcase_offsets(false).count(), expected.len());
    }

    // TODO: Tests for camelcase_offsets

    #[test]
    fn camelcase_words_basic_function() {
        check_camelcase_words("fooBar", &["foo", "Bar"]);
        check_camelcase_words("FooBar", &["Foo", "Bar"]);
        check_camelcase_words("AndroidVM", &["Android", "VM"]);
        check_camelcase_words("RARFile", &["RAR", "File"]);
        check_camelcase_words("ADruidsDuel", &["A", "Druids", "Duel"]);
        check_camelcase_words("PickACard", &["Pick", "A", "Card"]);
        check_camelcase_words("AxelF", &["Axel", "F"]);
    }

    #[test]
    fn camelcase_words_leaves_capitalization_alone() {
        check_camelcase_words("foo", &["foo"]);
        check_camelcase_words("Foo", &["Foo"]);
        check_camelcase_words("fooBar", &["foo", "Bar"]);
        check_camelcase_words("FooBar", &["Foo", "Bar"]);
        check_camelcase_words("foo bar", &["foo", "bar"]);
        check_camelcase_words("Foo Bar", &["Foo", "Bar"]);
    }

    #[test]
    fn camelcase_words_ascii_number_handling() {
        check_camelcase_words("6LittleEggs", &["6", "Little", "Eggs"]);
        check_camelcase_words("the12chairs", &["the", "12", "chairs"]);
        check_camelcase_words("The12Chairs", &["The", "12", "Chairs"]);
        check_camelcase_words("1.5 Children", &["1.5", "Children"]);
        check_camelcase_words("The1.5Children", &["The", "1.5", "Children"]);
        check_camelcase_words("the1.5children", &["the", "1.5", "children"]);
        check_camelcase_words("Version1.1", &["Version", "1.1"]);
        check_camelcase_words("catch22", &["catch", "22"]);
        check_camelcase_words("Catch22", &["Catch", "22"]);
        check_camelcase_words("1Two3", &["1", "Two", "3"]);
        check_camelcase_words("One2Three", &["One", "2", "Three"]);
        check_camelcase_words("ONE2", &["ONE", "2"]);
        check_camelcase_words("ONE2THREE", &["ONE", "2", "THREE"]);
    }

    #[test]
    fn camelcase_words_basic_unicode_handling() {
        check_camelcase_words("\u{1D7DE}ŁittléEggs", &["\u{1D7DE}", "Łittlé", "Eggs"]);
        check_camelcase_words("ⅥŁittłeEggs", &["Ⅵ", "Łittłe", "Eggs"]);
        check_camelcase_words("➅LittleEggs", &["➅", "Little", "Eggs"]);
        check_camelcase_words("\u{1D7DE} Łittlé Eggs", &["\u{1D7DE}", "Łittlé", "Eggs"]);
        check_camelcase_words("Ⅵ Łittłe Eggs", &["Ⅵ", "Łittłe", "Eggs"]);
        check_camelcase_words("➅ Little Eggs", &["➅", "Little", "Eggs"]);
    }

    #[test]
    fn camelcase_words_titlecase_handling() {
        check_camelcase_words("ǅ", &["ǅ"]);
        check_camelcase_words("ǅxx", &["ǅxx"]);
        check_camelcase_words("ǅX", &["ǅ", "X"]);
        check_camelcase_words("Xǅ", &["X", "ǅ"]);
        check_camelcase_words("Xxǅ", &["Xx", "ǅ"]);
        check_camelcase_words("ǅXx", &["ǅ", "Xx"]);
        check_camelcase_words("1ǅ2", &["1", "ǅ", "2"]);
    }

    #[test]
    fn camelcase_words_ampersand_handling() {
        check_camelcase_words("TheKing&I", &["The", "King", "&", "I"]);
        check_camelcase_words("TheKing﹠I", &["The", "King", "﹠", "I"]);
        check_camelcase_words("TheKing＆I", &["The", "King", "＆", "I"]);
        check_camelcase_words("TheKing\u{1F674}I", &["The", "King", "\u{1F674}", "I"]);
        check_camelcase_words("A&b", &["A", "&", "b"]);
        check_camelcase_words("A﹠b", &["A", "﹠", "b"]);
        check_camelcase_words("A＆b", &["A", "＆", "b"]);
        check_camelcase_words("A\u{1F674}b", &["A", "\u{1F674}", "b"]);
        check_camelcase_words("1&2", &["1", "&", "2"]);
        check_camelcase_words("ǅ&ǅ", &["ǅ", "&", "ǅ"]);
        check_camelcase_words("Forsooth&'tisTrue", &["Forsooth", "&", "'tis", "True"]);
    }

    #[test]
    fn camelcase_words_apostrophe_handling() {
        check_camelcase_words("Don'tMove", &["Don't", "Move"]);
        check_camelcase_words("Don\u{2019}tMove", &["Don\u{2019}t", "Move"]);
        check_camelcase_words("Don\u{FF07}tMove", &["Don\u{FF07}t", "Move"]);
        check_camelcase_words("It's my kids' kids'", &["It's", "my", "kids'", "kids'"]);
        check_camelcase_words("it\u{2019}s my kids\u{2019} kids\u{2019}",
                                  &["it\u{2019}s", "my", "kids\u{2019}", "kids\u{2019}"]);
        check_camelcase_words("it\u{FF07}s my kids\u{FF07} kids\u{FF07}",
                                  &["it\u{FF07}s", "my", "kids\u{FF07}", "kids\u{FF07}"]);
    }

    #[test]
    fn camelcase_words_open_close_plus_upper_lower() {
        check_camelcase_words("Test [Hello]", &["Test", "[Hello]"]);
        check_camelcase_words("Test (Hello)", &["Test", "(Hello)"]);
        check_camelcase_words("Test {Hello}", &["Test", "{Hello}"]);
        check_camelcase_words("Test «Hello»", &["Test", "«Hello»"]);
        check_camelcase_words("Test <Hello>", &["Test", "<Hello>"]);
        check_camelcase_words("Test ﹤Hello﹥", &["Test", "﹤Hello﹥"]);
        check_camelcase_words("Test ＜Hello＞", &["Test", "＜Hello＞"]);
    }

    #[test]
    fn camelcase_words_open_close_handling() {
        check_camelcase_words("Who?Him!Really?Yeah!", &["Who?", "Him!", "Really?", "Yeah!"]);
        check_camelcase_words("100%Juice", &["100%", "Juice"]);
        check_camelcase_words("WeAre#1", &["We", "Are", "#1"]);
        check_camelcase_words("ShadowWarrior(2013)", &["Shadow", "Warrior", "(2013)"]);
        check_camelcase_words("Testy<foo>", &["Testy", "<foo>"]);
        check_camelcase_words("Testy﹤foo﹥", &["Testy", "﹤foo﹥"]);
        check_camelcase_words("Testy＜foo＞", &["Testy", "＜foo＞"]);
        check_camelcase_words("Testy«foo»", &["Testy", "«foo»"]);
        check_camelcase_words("SallyFace[linux]", &["Sally", "Face", "[linux]"]);
        check_camelcase_words("SallyFace[Linux]", &["Sally", "Face", "[Linux]"]);
        check_camelcase_words("TestyFoo{Bar}Baz", &["Testy", "Foo", "{Bar}", "Baz"]);
        check_camelcase_words("ShadowWarrior\u{FF08}2013\u{FF09}",
                                  &["Shadow", "Warrior", "\u{FF08}2013\u{FF09}"]);
        check_camelcase_words("[ǅxx]", &["[ǅxx]"]);
        check_camelcase_words(" [ǅxx] ", &["[ǅxx]"]);
    }

    #[test]
    fn camelcase_words_doesnt_subdivide_numbers() {
        check_camelcase_words("3.14", &["3.14"]);
        check_camelcase_words("255", &["255"]);
        check_camelcase_words("1000000", &["1000000"]);
        check_camelcase_words("ut2003", &["ut", "2003"]);
    }

    #[test]
    fn camelcase_words_unicode_segmentation() {
        // Zalgo text generated using http://eeemo.net/
        check_camelcase_words("f̴͘͟͜ǫ̴̸̧͘ó̵̢̢͏B̴̨͠á̵̸͡r̶̵͢͠", &["f̴͘͟͜ǫ̴̸̧͘ó̵̢̢͏", "B̴̨͠á̵̸͡r̶̵͢͠"]);
        check_camelcase_words("Ŕ̀̕͟͞À̸̛͞͞Ŕ̨̕F̕͜͟͠í̵͜l҉̨e̶̵", &["Ŕ̀̕͟͞À̸̛͞͞Ŕ̨̕", "F̕͜͟͠í̵͜l҉̨e̶̵"]);
        check_camelcase_words("P̕͟͠i҉͢c̨̨͞͡ḱ̸̕Ą̸Ç͘͜a͘͟r̀͟͢҉̵d̕͜", &["P̕͟͠i҉͢c̨̨͞͡ḱ̸̕", "Ą̸", "Ç͘͜a͘͟r̀͟͢҉̵d̕͜"]);
        check_camelcase_words("6̢L̢͏͏͠i̷̛͜t̷̕t̷͟ļ͟͢ȩ̨̕̕È̷̸g̵̷̨͢͡g̷s͟͞", &["6̢", "L̢͏͏͠i̷̛͜t̷̕t̷͟ļ͟͢ȩ̨̕̕", "È̷̸g̵̷̨͢͡g̷s͟͞"]);
        check_camelcase_words("t̶̨͞h̨͝͝e̡͟͢1̴̧̀͘͟2͘͘c̷̴̢͘h̶̴̢͢à͘͏i̡̛r͜s̷͏", &["t̶̨͞h̨͝͝e̡͟͢", "1̴̧̀͘͟2͘͘", "c̷̴̢͘h̶̴̢͢à͘͏i̡̛r͜s̷͏"]);
        check_camelcase_words("T̶͡ḩ̷̷͟ȩ̛́͘͡1̵̨̕͢2̕͝C̸̡͞͏͟h̴̵̀a҉͜͢i̵̸̡̕ŗ̴͢s̴͏͘͡", &["T̶͡ḩ̷̷͟ȩ̛́͘͡", "1̵̨̕͢2̕͝", "C̸̡͞͏͟h̴̵̀a҉͜͢i̵̸̡̕ŗ̴͢s̴͏͘͡"]);
        check_camelcase_words("T͠҉̸̷h̀͡e̡̨͝͠1̴́͏.͏̨́͠͝5̨́̕C̷͜͏͠h̢̧͝ì̡̢̕l̸͞͡d̵̕͢͡ŕ̶͘͡͞e͜͝n̨҉̕", &["T͠҉̸̷h̀͡e̡̨͝͠", "1̴́͏.͏̨́͠͝5̨́̕", "C̷͜͏͠h̢̧͝ì̡̢̕l̸͞͡d̵̕͢͡ŕ̶͘͡͞e͜͝n̨҉̕"]);
        check_camelcase_words("t̡̛͟h͏҉҉́è͝͠1̢̕͟͟.̶̛5̶͜ć̀ḩ̶̸̕͜i̸̕͢l̢͡͝͝͏d͘͟r̨͢e̢҉̵͞͠n̛", &["t̡̛͟h͏҉҉́è͝͠", "1̢̕͟͟.̶̛5̶͜", "ć̀ḩ̶̸̕͜i̸̕͢l̢͡͝͝͏d͘͟r̨͢e̢҉̵͞͠n̛"]);
        check_camelcase_words("V̶͞e̡͜͟͠r̢͟s̀͏̧̢̕i̸̧͞͠o̷̸̧n̡͞1̧̀͘͟͞.̸̕1́͞҉", &["V̶͞e̡͜͟͠r̢͟s̀͏̧̢̕i̸̧͞͠o̷̸̧n̡͞", "1̧̀͘͟͞.̸̕1́͞҉"]);
        check_camelcase_words("A̴&͏̵̛b͝", &["A̴", "&͏̵̛", "b͝"]);
        check_camelcase_words("u̢҉͡t̸̷̛2̶͏͡0́̕҉̶0̡͞͡3̴̷͟", &["u̢҉͡t̸̷̛", "2̶͏͡0́̕҉̶0̡͞͡3̴̷͟"]);
    }
}
