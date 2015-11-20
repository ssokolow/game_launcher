"""Routines for inferring a game's name"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import os, re

# Source: http://stackoverflow.com/a/9283563
# (With a tweak to let numbers start new words)
camelcase_re = re.compile(r'((?<=[a-z])[A-Z0-9]|(?<!\A)[A-Z](?=[a-z]))')

# Used by L{titlecase_up} to find word-starting lowercase letters
wordstart_re = re.compile(r'(^|[. _-])[a-z]')

# TODO: Unit tests for these regexes, separate from the integrated one
fname_re_fragments = {
    's': '([ _-])',  # Whitespace
    'ver': '(v?\d+([._]\d+)+([a-zA-Z])*|v\d+)',
    'phase_full': '(alpha|beta|(?![a-zA-Z])rc|build[ _-]\d+)',
    'build': '(full|standalone|humble|glibc\d+)',
    'platform': '(lin(ux?)(32|64)?|x64|x86_64)',
}
fname_re_fragments['phase'] = ('(a|b(?!uild)|%(phase_full)s)'
                               % fname_re_fragments)

fname_ver_re = re.compile(r"""%(s)s*(
        %(phase)s %(ver)s|
        %(phase)s \d+[a-zA-Z]|
        %(ver)s (%(s)s %(phase)s %(s)s? \d)? (%(s)s %(platform)s)?|
        %(platform)s? %(s)s \d{6}\d*$|
        %(platform)s %(s)s (\d+(?!\.))|
        %(build)s %(s)s? %(ver)s?|
        %(ver)s|
        (%(phase_full)s %(s)s)? %(platform)s (%(s)s %(ver)s %(phase)s?)?|
        ([ _-]|\b)gog([ _-]|\b)
    )""" % fname_re_fragments, re.IGNORECASE | re.VERBOSE)
fname_whitespace_re = re.compile(r"[ _-]")
fname_whitespace_nodash_re = re.compile(r"[ _]")
fname_numspacing_re = re.compile(r'([a-zA-Z])(\d)')
fname_subtitle_start_re = re.compile(r"(\d)(\s\w)")

# TODO: Find some way to do a coverage test for this.
# TODO: Split this out into a shared constants module
PROGRAM_EXTS = (
    '.air', '.swf', '.jar',
    '.sh', '.py', '.pl',
    '.exe', '.bat', '.cmd', '.pif',
    '.bin',
    '.desktop',
    # Note: .com is intentionally excluded because they're so rare outside of
    #       DOSBox and I worry about the potential for false positives caused
    #       by it showing up in some game's clever title.
)

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
    r'Or ': 'or ',
    r's ': "'s ",
    r'Scumm VM': 'ScummVM',
    r' The\b': ' the',
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

def titlecase_up(in_str):
    """A C{str.title()} analogue which won't mess up acronyms like FTL."""
    return wordstart_re.sub(lambda x: x.group(0).upper(), in_str)

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

    # Remove version information
    name = fname_ver_re.sub('', fname)

    # Convert whitespace cues
    if fname_whitespace_re.search(name):
        if ' ' in name or '_' in name:
            # Make sure things like "X-Com Collection" are handled properly
            name = fname_whitespace_nodash_re.sub(' ', name)
        else:
            # ...but also handle names using dashes as separators properly
            name = fname_whitespace_re.sub(' ', name)
    else:
        # ...and names using CamelCase
        name = camelcase_re.sub(r' \1', name)

    # Titlecase... but only in one direction so things like "FTL" remain
    name = titlecase_up(name)

    # Ensure numbers are preceeded by a space (eg. "Trine2" -> "Trine 2")
    name = fname_numspacing_re.sub(r'\1 \2', name)

    # Assume that a number followed by a space and more text marks the
    # beginning of a subtitle and add a colon
    name = fname_subtitle_start_re.sub(r"\1:\2", name)

    # Assume that it's either an acronym or Ys, which is handled by overrides
    if len(name) < 3:
        name = name.upper()

    # Fix capitalization anomalies broken by whitespace conversion
    name = re.sub('|'.join(WHITESPACE_OVERRIDES), _apply_ws_overrides, name)

    return name

# vim: set sw=4 sts=4 expandtab :
