//! Routines for parsing camelcase strings
//!

use regex::Regex;
use unicode_segmentation::UnicodeSegmentation;
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

/// Phase 1 intermediate representation used to separate classifying Unicode grapheme clusters from
/// defining state transitions between classes.
#[derive(PartialEq)]
enum CharType {
    /// No data has yet been processed
    Start,
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
    /// A decimal separator, thousands separator, or other "Common Number Separator"
    NumSep,
    /// A piece of punctuation which should not have a space after it, such as "(" or "#"
    StartPunct,
    /// A piece of punctuation which should not have a space before it, such as ")" or "%"
    EndPunct,
    /// A whitespace character
    Space,
    /// Any character which does not fall into the other classes
    Other
}

/// Phase 2 intermediate representation used to separate defining state transitions between
/// character classes from actually processing the text to apply the defined transitions.
#[derive(PartialEq)]
enum CCaseAction {
    /// Pass the character through without any changes
    Literal,
    /// Insert a space before the character
    SpaceBefore,
    /// Insert a space before the previous character, if it was `Defer`ed
    SpaceDeferred,
    /// Delay passing the character through until the following character is identified
    Defer
}

// --== Loose Functions ==--

/// Identify what role a given character plays in the string
fn classify_char(in_char: char) -> CharType {
    match in_char {
        // TODO: Find a crate to which I can delegate "BIDI" category membership checking
        //       (Membership checked at http://www.unicode.org/Public/UNIDATA/UnicodeData.txt)

        x if x.is_whitespace() => CharType::Space,

        // TODO: Is there any database I can use to delegate "Ampersand" and "Apostrophe" DefN?
        '\u{26}' | '\u{FE60}' | '\u{FF06}' | '\u{1F674}' => CharType::Ampersand,

        // NOTE: U+2019 (Right Single Quotation Mark)" is included here because FileFormat.info
        //       includes "U+2019 is preferred for apostrophe" in the "Comments" field.
        '\u{27}' | '\u{2019}' | '\u{FF07}' => CharType::Apostrophe,

        // Include "BIDI: Common Number Separators [CS]" as non-space-inducing
        // TODO: Add unit tests for all of these
        '\u{2c}' | '\u{2e}' | '\u{2f}' | '\u{3a}' | '\u{a0}' | '\u{60c}' | '\u{202f}' |
                   '\u{2044}' | '\u{FE50}' | '\u{FE52}' | '\u{FE55}' | '\u{FF0C}' |
                   '\u{FF0E}' | '\u{FF0F}' | '\u{FF1A}' |

        // Include "BIDI: ES" as non-space-inducing characters based on test corpus
        // TODO: Add unit tests for all of these
                    '\u{2b}' | '\u{2d}' | '\u{207A}' | '\u{207B}' | '\u{208A}' | '\u{208B}' |
                    '\u{2212}' | '\u{FB29}' | '\u{FE62}' | '\u{FE63}' | '\u{FF0B}' | '\u{FF0D}'
            => CharType::NumSep,

        // Punctuation which should only trigger whitespace on one side
        // TODO: Add unit tests for all of these
       '\u{23}' | '\u{FE5F}' | '\u{A1}' | '\u{BF}' | '\u{2E18}' | '\u{FF03}' | '\u{1F679}'
           => CharType::StartPunct,
       '\u{21}' | '\u{25}' | '\u{3b}' | '\u{3f}' | '\u{2030}' | '\u{2031}' | '\u{203c}' |
                  '\u{203d}' | '\u{2047}' | '\u{2048}' | '\u{2049}' | '\u{2762}' | '\u{FE54}' |
                  '\u{FE56}' | '\u{FE57}' | '\u{FE6A}' | '\u{FF01}' | '\u{FF05}' | '\u{FF1B}' |
                  '\u{FF1F}'
           => CharType::EndPunct,
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
    // TODO: Rewrite this as a wordwise iterator so count and space-insertion both come free

    // State for basic comparisons like "lowercase followed by uppercase"
    let mut prev_type = CharType::Start;

    // State for deferred space insertion (For "ABc", "c" triggers insertion BEFORE "B")
    let mut prev_cluster = "";
    let mut prev_action = CCaseAction::Literal;

    // Output accumulator (TODO: Don't just guess at how much slack to allocate)
    let mut output = String::with_capacity(in_str.len().saturating_add(6));

    for grapheme_cluster in in_str.graphemes(true) {
        // Extract the base `char` so we can call things like is_uppercase()
        let base = grapheme_cluster.chars().nth(0).expect("non-empty grapheme cluster");

        // Identify character types for comparison
        let curr_type = classify_char(base);

        // Determine what action to take for each transition type
        // FIXME: Silence `match_same_arms` lint. It could prompt someone to mess with precedence.
        let curr_action = match (&prev_type, &curr_type) {
            // Don't insert a space at the beginning or where one already exists
            // (This match arm must come first in the listi)
            // TODO: Actually collapse and normalize whitespace
            (&CharType::Start, _) |
            (&CharType::Space, _) | (_, &CharType::Space) => CCaseAction::Literal,

            // Always insert space before and after ampersands
            // (This match arm must come after Start/Space but before NumSep/etc.)
            // TODO: Unit test the interaction between Ampersand and NumSep/etc.
            (&CharType::Ampersand, _) | (_, &CharType::Ampersand) => CCaseAction::SpaceBefore,

            // Don't insert space around a "Common Number Separator" or apostrophe
            // or after opening or before closing punctuation (eg. parens)
            (&CharType::NumSep, _) | (_, &CharType::NumSep) |
            (&CharType::Apostrophe, _) | (_, &CharType::Apostrophe) |
            (&CharType::StartPunct, _) | (_, &CharType::EndPunct) => CCaseAction::Literal,

            // Defer space insertion between uppercase characters until we know whether the second
            // is starting a new word
            (&CharType::Uppercase, &CharType::Uppercase) => CCaseAction::Defer,

            // Don't insert a space after the first letter of a new word
            (&CharType::Titlecase, &CharType::Lowercase) |
            (&CharType::Uppercase, &CharType::Lowercase) => CCaseAction::SpaceDeferred,

            // If we reach this point and the character types differ, insert a space.
            (x, y) if x != y => CCaseAction::SpaceBefore,

            // ...otherwise, just pass it through verbatim
            _ => CCaseAction::Literal
        };

        // Actually take action
        if prev_action == CCaseAction::Defer {
            if curr_action == CCaseAction::SpaceDeferred {
                    output.push(' ');
            }
            output.push_str(prev_cluster);
        }
        if curr_action != CCaseAction::Defer {
            if curr_action == CCaseAction::SpaceBefore {
                output.push(' ');
            }
            output.push_str(grapheme_cluster);
        };

        // Set up for the next iteration
        prev_type = curr_type;
        prev_action = curr_action;
        prev_cluster = grapheme_cluster;
    }

    // If the last character was `Defer`ed, flush it into the output string
    if prev_action == CCaseAction::Defer {
        output.push_str(prev_cluster);
    }

    // Return the final result
    output
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
        let in_str2 = CAMELCASE_RE.replace_all(in_str, CAMELCASE_COUNT_REPLACEMENT);
        CAMELCASE_RE.replace_all(&in_str2, CAMELCASE_COUNT_REPLACEMENT).count_char('\0')
}

// --== Tests ==--

#[cfg(test)]
mod tests {
    use super::camelcase_to_spaces;

    // -- camelcase_to_spaces --
    // TODO: Now that I have a better understanding of the state machine underlying CamelCase,
    //       I should refactor these tests to be more comprehensive and less duplication-heavy.

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
        check_camelcase_to_spaces("SallyFace[Linux]", "Sally Face [Linux]");
        check_camelcase_to_spaces("TestyFoo{Bar}Baz", "Testy Foo {Bar} Baz");
        check_camelcase_to_spaces("ShadowWarrior\u{FF08}2013\u{FF09}",
                                  "Shadow Warrior \u{FF08}2013\u{FF09}");
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
