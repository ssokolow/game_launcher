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
wordstart_re = re.compile(r'(^|[ -])[a-z]')

# TODO: Unit tests for these regexes, separate from the integrated one
fname_ver_re = re.compile(r"""[ _-]*(
        [ _-](alpha|beta|v|build[ _-]?)?\d+(\.\d+|[a-zA-Z])*
            ((a|b|alpha|beta|rc|build)\d+)?|
        (alpha|beta)\D|
        lin(ux)?(32|64|\b)|
        linux?(32|64)?|
        x64|
        standalone|
        humble|
        ([ _-]|\b)gog([ _-]|\b)
    )""", re.IGNORECASE | re.VERBOSE)
fname_whitespace_re = re.compile(r"[ _-]")
fname_whitespace_nodash_re = re.compile(r"[ _]")

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
# TODO: Find some way to do a coverage test for this.
WHITESPACE_OVERRIDES = {
    r'Db\b': 'DB',
    r'Djgpp': 'DJGPP',
    r'IN Vedit': 'INVedit',
    r'Mc ': 'Mc',
    r'Mac ': 'Mac',
    r'Ux\b': 'UX',
    r'iii\b': ' III',
    r' I V': 'IV',
    r' V I': 'VI',
    r' V M': 'VM',
    r'xwb': 'XWB',
}

# Map used by L{filename_to_name}'s single-pass approach to using
# WHITESPACE_OVERRIDES.
_WS_OVERRIDE_MAP = {x.replace(r'\b', ''): y for x, y
                    in WHITESPACE_OVERRIDES.items()}

def titlecase_up(in_str):
    """A C{str.title()} analogue which won't mess up acronyms."""
    return wordstart_re.sub(lambda x: x.group(0).upper(), in_str)

def filename_to_name(fname):
    """A heuristic transform to produce pretty good titles from filenames
    without relying on out-of-band information.
    """
    # Remove recognized program extensions
    fbase, fext = os.path.splitext(fname)
    if fext.lower() in PROGRAM_EXTS:
        fname = fbase

    # Remove version information
    name = fname_ver_re.sub('', fname)

    # Convert whitespace cues
    if fname_whitespace_re.search(name):
        if ' ' in name or '_' in name:
            name = fname_whitespace_nodash_re.sub(' ', name)
        else:
            name = fname_whitespace_re.sub(' ', name)
    else:
        name = camelcase_re.sub(r' \1', name)

    # Titlecase... but only in one direction so things like "FTL" remain
    name = titlecase_up(name)

    # Fix capitalization anomalies broken by whitespace conversion
    name = re.sub('|'.join(WHITESPACE_OVERRIDES),
                  lambda x: _WS_OVERRIDE_MAP[x.group(0)], name)

    return name

# vim: set sw=4 sts=4 expandtab :
