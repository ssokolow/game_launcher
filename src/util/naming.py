"""Routines for inferring a game's name"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import os, re

import src.core
titlecase_up = src.core.util.naming.titlecase_up
normalize_whitespace = src.core.util.naming.normalize_whitespace

# Source: http://stackoverflow.com/a/9283563
# (With a tweak to let numbers start new words)
camelcase_re = re.compile(r'((?<=[a-z])[A-Z0-9]|(?<!\A)[A-Z](?=[a-z]))')

# Used by L{titlecase_up} to find word-starting lowercase letters
wordstart_re = re.compile(r'(^|[. _-])[a-z]')

# TODO: Unit tests for these regexes, separate from the integrated one
fname_whitespace_re = re.compile(r"[ _-]")
fname_whitespace_nodash_re = re.compile(r"[ _]")
fname_numspacing_re = re.compile(r'([a-zA-Z])(\d)')
fname_subtitle_start_re = re.compile(r"(\d)(\s\w{2,})")

import src.core
INSTALLER_EXTS = src.core.util.constants.INSTALLER_EXTS
PROGRAM_EXTS = src.core.util.constants.PROGRAM_EXTS

ACRONYM_OVERRIDES = ['Ys']

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

literal_cruft = ['gog', 'setup']
tail_cruft_tokens = ['full']  # Only cruft as the last token while postproc-ing
tail_cruft_internal = ['32bit', '64bit', 'alpha', 'amd64', 'beta', 'drm',
                       'drmfree', 'glibc', 'humble', 'installer', 'standalone',
                       'stdalone', 'ubuntu', 'x64', 'x86', 'x86_64']
post_re = re.compile('''(^|\b)(version|gamma\d+|indev|0($|\b)|
                        update\d+|wml|[lw]in(ux|32|64|($|\b))|lnx|
                        default|(a|b|rc)\d+|v\d+|\d+\.|\d+(\.\d+)+)|\d{5,}|
                     ''' + '|'.join(tail_cruft_internal),
                     re.I | re.VERBOSE)
def strip_ver_experimental(fname):
    # Recognize and fix escaped colons
    fname = re.sub(r'(\w)_\s+(\w)', r'\1: \2', fname)

    tokens = normalize_whitespace(fname).split()

    # Remove pre-cruft
    tokens = [x for x in tokens if x.lower() not in literal_cruft]

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

    for substr in tail_cruft_internal:
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
        # TODO: Make this generic
        if word.lower() in fname.lower() and word.lower() not in name.lower():
            name = "{} {}".format(name, word)

    return name

# vim: set sw=4 sts=4 expandtab :
