"""Sub-plugin to extract metadata from GOG.com start.sh scripts.

Copyright (C) 2014-2015 Stephan Sokolow

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

import os
from ..common import GameLauncher
from ...util.naming import titlecase_up
from ...util.executables import Roles
from ...util.shlexing import (script_precheck, lex_shellscript,
                              make_metadata_mapper)

BACKEND_NAME = "GOG.com"

def detect_gogishness(token_list, fields):
    """Set the sub_provider field if the shell script sources
       C{support/gog_com.shlib}"""
    if token_list and token_list[0] == 'source':
        if ''.join(token_list[1:]) == 'support/gog_com.shlib':
            fields['sub_provider'] = BACKEND_NAME

    # TODO: Rework this so I can explicitly specify roles here
    if len(token_list) >= 5 and token_list[0] == 'define_option':
        tlist = token_list[3].split()
        for prefix in ('start', '$game_name', '${game_name}'):
            if tlist[0].lower() == prefix:
                tlist.pop(0)
        if tlist and tlist[-1].lower() == '[default]':
            tlist.pop()
        token_list[3] = ' '.join(tlist).strip()

        if not token_list[3] or token_list[3].lower() == '[default]':
            token_list[3] = 'Play'

        fields.setdefault('commands', []).append(
            (titlecase_up(token_list[3]), token_list[2]))


def inspect(path):
    """Try to extract GOG.com tarball metadata from the given folder"""
    start_path = os.path.join(path, 'start.sh')
    if not script_precheck(start_path):
        return None

    fields = lex_shellscript(start_path, make_metadata_mapper({
        'GAME_NAME': 'name',
        'PACKAGE_NAME': 'game_id'
    }, detect_gogishness))

    icon_path = os.path.join(path, 'support', fields['game_id'] + '.png')
    if os.path.isfile(icon_path):
        fields['icon'] = icon_path

    # TODO: Detect and offer start.sh subcommands
    # TODO: Detect things like Manual.pdf and generate subcommands
    fields['commands'] = [GameLauncher(
        argv=[start_path, x[1]],
        name=x[0],
        provider=BACKEND_NAME,
        tryexec=start_path,
        use_terminal=False) for x in fields['commands']]

    fields['commands'].extend([
        GameLauncher(name="Install", argv=[start_path, '--install-deb'],
                     provider=BACKEND_NAME,
                     role=Roles.install),
        GameLauncher(name="Uninstall", argv=[start_path, '--uninstall'],
                     provider=BACKEND_NAME,
                     role=Roles.uninstall)
    ])

    return fields
