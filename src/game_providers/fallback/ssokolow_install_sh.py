"""Sub-plugin to extract metadata from my install.sh scripts.

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

import os, logging
from ..common import GameLauncher
from ...util.common import resolve_exec
from ...util.executables import Roles
from ...util.shlexing import (script_precheck, lex_shellscript,
                              make_metadata_mapper)

BACKEND_NAME = "ssokolow's install.sh"
log = logging.getLogger(__name__)

def inspect(path):
    """Try to extract install.sh metadata from the given folder"""
    install_path = os.path.join(path, 'install.sh')
    if not script_precheck(install_path):
        return None

    metadata_map = {
        'GAME_ID': 'game_id',  # TODO: Decide how to support this
        'GAME_NAME': 'name',
        'GAME_SYNOPSIS': 'description',
        'GAME_EXEC': 'argv',
        'ICON_PATH': 'icon',
        'CATEGORIES': 'categories',
    }
    fields = lex_shellscript(install_path, make_metadata_mapper(metadata_map))
    if 'categories' in fields:
        fields['categories'] = fields['categories'].strip(';').split(';')

    for fname in fields:
        for varname, varkey in metadata_map.items():
            ref = '$' + varname
            if ref in fields[fname]:
                fields[fname] = fields[fname].replace(ref, fields[varkey])

    if all(x in fields for x in metadata_map.values()):
        # TODO: Decide how to support this
        pass  # fields['sub_provider'] = BACKEND_NAME
    else:
        log.debug("Unrecognized install.sh: %s", install_path)
        return None

    try:
        fields['argv'] = resolve_exec(fields['argv'], rel_to=path)
    except KeyError:
        log.error("%s specifies no argv", path)
        raise

    if not os.path.exists(fields['icon']):
        fields['icon'] = os.path.join(path, fields['icon'])

    fields.update({
        'role': Roles.play,
        'provider': BACKEND_NAME,
        'tryexec': fields['argv'][0],
        'use_terminal': False
    })
    launcher = GameLauncher(**fields)
    installer = GameLauncher(name="Install",
                             role=Roles.install,
                             provider=BACKEND_NAME,
                             argv=[install_path])

    return {
        'name': launcher.name,
        'icon': launcher.icon,
        'base_path': path,
        'provider': BACKEND_NAME,
        'commands': [launcher, installer]
    }
