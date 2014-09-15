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

import shlex

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
