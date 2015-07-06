"""Routines for parsing shell scripts to extract metadata"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import os, shlex

# Don't search for metadata inside scripts like "start.sh" if they're bigger
# than this size.
MAX_SCRIPT_SIZE = 1024 ** 2  # 1 MiB

def script_precheck(path):
    """Basic checks which should be run before inspecting any script."""
    return os.path.isfile(path) and os.stat(path).st_size <= MAX_SCRIPT_SIZE

def lex_shellscript(script_path, statement_cb):
    """Given a file-like object, use a POSIX-mode shlex.shlex object to split
       it into statements and call the given statement processor to convert
       statements into dicts.

       Accepts either an individual callback or a lists or tuples of them.
    """
    fields = {}
    if not isinstance(statement_cb, (list, tuple)):
        statement_cb = [statement_cb]

    with open(script_path, 'r') as fobj:
        lexer = shlex.shlex(fobj, script_path, posix=True)
        lexer.whitespace = lexer.whitespace.replace('\n', '')

        token, current_statement = '', []
        while token is not None:
            token = lexer.get_token()
            if token in [None, '\n', ';']:
                for callbk in statement_cb:
                    callbk(current_statement, fields)
                current_statement = []
            else:
                current_statement.append(token)
    return fields

def make_metadata_mapper(field_map, extras_cb=None):
    """Closure to make simple C{statement_cb} functions for L{lex_shellscript}.

    @param field_map: A dict mapping shell variable names to C{fields} keys.
    @param extras_cb: A callback to perform more involved transformations.
    """

    def process_statement(token_list, fields):
        """A simple callback to convert lists of shell tokens into key=value
           pairs according to the contents of C{field_map}
        """
        if len(token_list) == 6 and token_list[0:3] == ['declare', '-', 'r']:
            if token_list[3] in field_map:
                fields[field_map[token_list[3]]] = token_list[5]
        elif len(token_list) == 3 and token_list[1] == '=':
            if token_list[0] in field_map:
                fields[field_map[token_list[0]]] = token_list[2]

        if extras_cb:
            extras_cb(token_list, fields)
    return process_statement

# vim: set sw=4 sts=4 expandtab :
