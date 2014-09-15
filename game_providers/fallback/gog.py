"""Sub-plugin to extract metadata from GOG.com start.sh scripts.

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

import os
from ..common import script_precheck
from .common import lex_shellscript, make_metadata_mapper

BACKEND_NAME = "GOG.com"

def detect_gogishness(token_list, fields):
    """Set the sub_provider field if the shell script sources
       C{support/gog_com.shlib}"""
    if token_list and token_list[0] == 'source':
        if ''.join(token_list[1:]) == 'support/gog_com.shlib':
            fields['sub_provider'] = BACKEND_NAME

def inspect(path):
    """Try to extract GOG.com tarball metadata from the given folder"""
    start_path = os.path.join(path, 'start.sh')
    if not script_precheck(start_path):
        return None

    fields = lex_shellscript(start_path, make_metadata_mapper({
        'GAME_NAME': 'name',
        'PACKAGE_NAME': 'game_id'
    }, detect_gogishness))

    fields['argv'] = start_path

    icon_path = os.path.join(path, 'support', fields['game_id'] + '.png')
    if os.path.isfile(icon_path):
        fields['icon'] = icon_path

    return fields
