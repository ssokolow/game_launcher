"""Routines for inferring a game's name"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import os, re

import src.core
camelcase_to_spaces = src.core.util.naming.camelcase_to_spaces
titlecase_up = src.core.util.naming.titlecase_up
normalize_whitespace = src.core.util.naming.normalize_whitespace

INSTALLER_EXTS = src.core.util.constants.INSTALLER_EXTS
PROGRAM_EXTS = src.core.util.constants.PROGRAM_EXTS
NON_BINARY_EXTS = src.core.util.constants.PROGRAM_EXTS

# TODO: Treat "+" similarly to "-" as a separator
# TODO: Figure out how to filter "steam" as a version token without trucating
#       names containing things like "of steam" or "and steam".
# TODO: Need a filter stage which throws out numeric-only tokens after the
#      first to accept things like "tbs_2_18_08" as "tbs 2"

# TODO: Unit tests for these regexes, separate from the integrated one
fname_numspacing_re = re.compile(r'([a-zA-Z])(\d)')
fname_subtitle_start_re = re.compile(r"(\d)(\s\w{2,})")

# TODO: Use these for Titlecase case-overriding instead of abusing
#       the WHITESPACE_OVERRIDES dict.
ARTICLES = ['a', 'an', 'the']
CONJUNCTIONS = ['for', 'and', 'but', 'or', 'yet', 'so']
PREPOSITIONS = [
    # English (intentionally limited to short words which have no major
    #          secondary use-case where lowercasing them would be incorrect)
    'as', 'at', 'but', 'by', 'for', 'in', 'of', 'on', 'to', 'up',
    # French words which might show up in artsy titles
    # (when not risking conflicting with English titlecase rules)
    'à', 'de', 'du', 'en',
]

# Words which shouldn't be treated as acronyms if they're the only thing
# before the first occurrence of a number
# (Given in the capitalization form they should be forced to)
ACRONYM_OVERRIDES = [x.title() for x in
                     ARTICLES + CONJUNCTIONS + PREPOSITIONS + ['Ys']]

# NOTE: These must be their *final* capitalization, as this process runs last
PRESERVED_VERSION_KEYWORDS = ['Client', 'Server']

# Overrides for common places where the L{filename_to_name} heuristic breaks
# TODO: Make sure I'm testing all of these cases
# TODO: Find some way to do a coverage test for this.
WHITESPACE_OVERRIDES = {
    r' - ': ': ',
    r'And ': 'and ',
    r' And The ': ' and the ',
    r'\bCant': "Can't",
    r'Db\b': 'DB',
    r'Djgpp': 'DJGPP',
    r'\bDont': "Don't",
    r'IN Vedit': 'INVedit',
    r'Mc ': 'Mc',
    r'Mac ': 'Mac',
    r'Of\b': 'of',
    r'^Open ': r'Open',
    r'For ': 'for ',
    r'Or ': 'or ',
    r's ': "'s ",
    r' S ': "'s ",
    r'Scumm VM': 'ScummVM',
    r' The\b': ' the',
    r': The\b': ': The',
    r'Ux\b': 'UX',
    r'xwb': 'XWB',
    r'iii\b': ' III',
    r' I V': 'IV',
    r' V I': 'VI',
    r' V M': 'VM',
    r'\bYS\b': 'Ys',
}

# Workaround for limitations in my current approach to generating
# _WS_OVERRIDE_MAP
WS_OVERRIDE_EXCEPTIONS = {
    r's ': (-4, re.compile(r"""(
        .{1,3}'s|         # Already possessive
        .{1,3}us|         # Latin-derived words like Virus
        .{1,2}ess|        # Feminine forms like goddess and actress
        cells|            # "cells" is more likely to be plural than possessive
        .{1,4}s[ ](of|\d) # Possessives aren't usually before "of" or numbers
    )""", re.IGNORECASE | re.VERBOSE)),
}

# Map used by L{filename_to_name}'s single-pass approach to using
# WHITESPACE_OVERRIDES.
_WS_OVERRIDE_MAP = {x.replace(r'\b', '').replace('^', ''): y for x, y
                    in WHITESPACE_OVERRIDES.items()}

def _apply_ws_overrides(match):
    """Callback for re.sub"""
    match_str = match.group(0)
    result = _WS_OVERRIDE_MAP[match_str]

    if match_str in WS_OVERRIDE_EXCEPTIONS:
        offset, pat = WS_OVERRIDE_EXCEPTIONS[match_str]
        abs_offset = max(0, match.start() + offset)
        subject = match.string[abs_offset:]
        if pat.match(subject):
            return match_str
    return result

# Substrings that are easier to mark before tokenization
pre_tokenization_filter = re.compile("""
    v_?(\d_?)+|                   # Versions with escaped periods (v...)
    [01]{1,2}_\d{1,2}(_\d{1,2})?| # Versions with escaped periods ([01]_m(_p)?)
    \d{4}-\d{2}-\d{2}|            # ISO 8601 dates
    [^ _-]+[ _-]version[ _-]|     # "... version"
    x86_64                        # "x86_64" before _ is used as a delimiter
""", re.IGNORECASE | re.VERBOSE)

# TODO: Unit test suites for these various rules

# Stuff which should be safe to remove when found as an arbitrary substring
# (ie. It shouldn't present a Scunthorpe problem in any reasonable filename)
# TODO: Actually use this directly
cruft_substrings = [
    # architecture names
    # (keep "x86", "ppc", "armv..." out of this list. I can imagine problems.)
    '32bit', '64bit', 'aarch64', 'amd64', 'i386', 'i486', 'i586', 'i686',
    'powerpc', 'ppc64', 'ppc64el', 'x86_64',

    # platform names
    # (keep "x86", "ppc", "armv..." out of this list. I can imagine problems.)
    'debian', 'freebsd', 'linux32', 'linux64', 'lnx32', 'lnx64', 'netbsd',
    'openbsd', 'ubuntu',
    'wml',  # Shorthand for Windows/Mac/Linux observed in the wild

    # release-type classifiers
    'drmfree', 'stdalone', 'nonsteam', 'setup',
]

# Stuff which should be safe to remove from the post-splitting list of tokens
# if we've handled our whitespace inference correctly, but can't be in
# cruft_substrings because they could present Scunthorpe problems.
cruft_tokens = [
    # architecture names which must only be matched as tokens
    # (eg. 'armv6' in "MaximumHarmV6.0".lower())
    'x86', 'ppc', 'armv6', 'armv7', 'armv7s', 'armv8',
    'armhf', 'armel', 'mips64', 'mips64el', 'mipsel', 'gnu', 'msvc',
    'musl',

    # Platform names which can't be matched as substrings because it'll leave
    # behind bits that are harder to classify (eg. "linux32" -> "32")
    'lin', 'lin32', 'lin64', 'linux', 'lnx', 'win', 'win32', 'win64',
    'nw',  # NW.js, as seen in the wild

    # release-type classifiers which could present a Scunthorpe problem
    'indev', 'patch',

    # country/language tokens which can't reasonably be confused for words
    # (ie. keep "en", "es", "de", "in", "it", and "us" out of this list)
    # (Also, keep "ca" out, because it could be a decomposed "ça")
    'br', 'deu', 'eng', 'esp', 'fr', 'fra', 'ger', 'ita', 'jp', 'jap', 'pl',
    'pt', "uk",
] + cruft_substrings

# Tokens which should be considered cruft only if they appear at the beginning
# (ie. "gog_game_name_1.0.sh" but not "frobnicate_gog_game.sh")
prefix_cruft_tokens = ['gog'] + cruft_tokens

# Stuff which should short-circuit the evaluation if found as a substring
inner_cruft_internal = [
    'drm', 'standalone', 'retail',
    'alpha', 'beta', 'installer', 'update', 'default',
    'glibc', 'humble', 'hb', 'hib',
    '\0'] + cruft_substrings

# Stuff that's only cruft when it shows up as the last token after the other
# processing stages have finished
tail_cruft_tokens = ['full', 'groupees', 'l', 'hilo', 'steam', 'darwin',
                     ] + cruft_tokens

tokens_rx = """(^|\b)(
    gamma\d+|update\d+|
    (jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dev)\d{2}\d{2}?|
    (a|b|rc)\d+|\d{2}(\d{2})?-\d{2}-\d{2}|v\d+|
    \d+\.|r\d+|
""" + '|'.join(re.escape(x) for x in cruft_tokens) + ")($|\b)"

post_re = re.compile(tokens_rx + """|(v\.?)?\d+(\.\d+)+|\d{5,}|""" +
    '|'.join(inner_cruft_internal), re.IGNORECASE | re.VERBOSE)

def strip_ver_experimental(fname):
    # Recognize and fix escaped colons
    fname = re.sub(r'(\w)_\s+(\w)', r'\1: \2', fname)

    # Use \0 to mark replaced unwanted substrings
    # (Since its role in C matches what the heuristic uses such substrings for)
    fname = pre_tokenization_filter.sub('\0', fname).split('\0', 1)[0]

    tokens = normalize_whitespace(fname).split()

    # Remove pre-cruft without terminating processing
    while tokens and tokens[0].lower() in prefix_cruft_tokens:
        tokens.pop(0)

    if not tokens:
        return ''

    # whitelist the first non-pre-cruft token
    # (Needed to prevent over-filtering in cases like RaceTheSunLINUX_1.441
    #  when operating on a principle that whitespace surrogates like
    #  underscores should suppress camelcase splitting.)
    output, tokens = [tokens[0]], tokens[1:]
    for token in tokens:
        # Stop at the first post-cruft token
        if post_re.search(token):
            break
        output.append(token)

    # Filter leftover separating dashes
    while output:
        if output[-1] == '-':
            output = output[:-1]
        elif output[-1][-1] in '-_.':
            output[-1] = output[-1][:-1]
        elif output[-1] in tail_cruft_tokens:
            output = output[:-1]
        else:
            break

    for substr in inner_cruft_internal:
        if output[-1].lower().endswith(substr):
            output[-1] = output[-1][:-len(substr)]

    return ' '.join(output)

# TODO: Make sure I'm properly testing all branches of this
def filename_to_name(fname):
    """A heuristic transform to produce pretty good titles from filenames
    without relying on out-of-band information.
    """
    # Remove recognized program extensions
    # (But not others because periods may appear in the game name)
    fbase, fext = os.path.splitext(fname)
    if fext.lower() in PROGRAM_EXTS:
        fname = fbase

    # Remove version information and convert whitespace cues
    # (Two passes required to reliably deal with semi-CamelCase filenames)
    name = strip_ver_experimental(fname)
    name = normalize_whitespace(name)
    name = strip_ver_experimental(name)

    # Titlecase... but only in one direction so things like "FTL" remain
    name = titlecase_up(name)

    # Ensure numbers are preceeded by a space (eg. "Trine2" -> "Trine 2")
    name = fname_numspacing_re.sub(r'\1 \2', name)

    # Assume that a number followed by a space and more text marks the
    # beginning of a subtitle and add a colon
    name = fname_subtitle_start_re.sub(r"\1:\2", name)

    tokens = name.split(':')[0].split()
    for idx, token in list(enumerate(tokens))[::-1]:
        if re.search('[a-zA-Z]', token):
            alpha_len = len(' '.join(tokens[:idx + 1]))
            break
    else:
        alpha_len = 0

    # Optimization for AM2R which should theoretically have more applicability
    collapsed_name = name.replace(' ', '')
    if len(collapsed_name) < 5:
        name = collapsed_name

    if alpha_len < 3 and name[:alpha_len] not in ACRONYM_OVERRIDES:
        name_prefix = ''.join('{}.'.format(x) for x in name[:alpha_len])
        name = name_prefix.upper() + name[alpha_len:]
    elif alpha_len < 4:
        # Assume that it's either an acronym or Ys, which is fixed by overrides
        name = name.upper()
    elif alpha_len > 6 and name.upper() == name:
        # Assume anything entirely uppercase and longer than 6 characters is
        # a non-acronym (and sacrifice titles that are stylistically all-upper)
        name = name.title()

    # Fix capitalization anomalies broken by whitespace conversion
    name = re.sub('|'.join(WHITESPACE_OVERRIDES), _apply_ws_overrides, name)

    for word in PRESERVED_VERSION_KEYWORDS:
        if word.lower() in fname.lower() and word.lower() not in name.lower():
            name = "{} {}".format(name, word)

    return name

# vim: set sw=4 sts=4 expandtab :
