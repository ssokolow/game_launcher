"""Common routines for sub-backends.

Copyright (C) 2014 Stephan Sokolow

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import os, re, shlex

# @todo: Unit tests for these regexes, separate from the integrated one
fname_ver_re = re.compile(r"""[ _-]*(
        [ _-](alpha|beta)?\d+(\.\d+|[a-zA-Z])*((a|b|alpha|beta|rc)\d+)?|
        (alpha|beta)\D|
        lin(ux)?(32|64)?|
        standalone
    )""", re.IGNORECASE | re.VERBOSE)
fname_whitespace_re = re.compile(r"[ _-]")
fname_whitespace_nodash_re = re.compile(r"[ _]")

# Source: http://stackoverflow.com/a/9283563
# (With a tweak to let numbers start new words)
camelcase_re = re.compile(r'((?<=[a-z])[A-Z0-9]|(?<!\A)[A-Z](?=[a-z]))')

# Used by L{titlecase_up} to find word-starting lowercase letters
wordstart_re = re.compile(r'(^|[ -])[a-z]')

# @todo: Find some way to do a coverage test for this.
PROGRAM_EXTS = (
    '.swf', '.jar',
    '.sh', '.py', '.pl',
    '.exe', '.cmd', '.pif',
    '.bin',
    '.desktop',
)

# Overrides for common places where the L{filename_to_name} heuristic breaks
# @todo: Find some way to do a coverage test for this.
WHITESPACE_OVERRIDES = {
    r'Db\b': 'DB',
    r'IN Vedit': 'INVedit',
    r'Mc ': 'Mc',
    r'Mac ': 'Mac',
    r'Ux\b': 'UX',
    r'iii\b': 'III',
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

def lex_shellscript(script_path, statement_cb):
    """Given a POSIX-mode shlex.shlex object, split it into statements and
        call the given statement processor to convert statements into dicts.
    """
    fields = {}

    with open(script_path, 'r') as fobj:
        lexer = shlex.shlex(fobj, script_path, posix=True)
        lexer.whitespace = lexer.whitespace.replace('\n', '')

        token, current_statement = '', []
        while token is not None:
            token = lexer.get_token()
            if token in [None, '\n', ';']:
                fields.update(statement_cb(current_statement))
                current_statement = []
            else:
                current_statement.append(token)
    return fields

def make_metadata_mapper(field_map, extras_cb=None):
    """Closure to make simple C{statement_cb} functions for L{lex_shellscript}.

    @param field_map: A dict mapping shell variable names to C{fields} keys.
    @param extras_cb: A callback to perform more involved transformations.
    """

    def process_statement(token_list):
        """A simple callback to convert lists of shell tokens into key=value
           pairs according to the contents of C{field_map}
        """
        fields = {}
        if len(token_list) == 6 and token_list[0:3] == ['declare', '-', 'r']:
            if token_list[3] in field_map:
                fields[field_map[token_list[3]]] = token_list[5]
        elif len(token_list) == 3 and token_list[1] == '=':
            if token_list[0] in field_map:
                fields[field_map[token_list[0]]] = token_list[2]

        if extras_cb:
            extras_cb(token_list, fields)
        return fields
    return process_statement

# vim: set sw=4 sts=4 expandtab :
