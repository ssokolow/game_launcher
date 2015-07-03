"""Code to retrieve a list of installed games from PlayOnLinux

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

@todo: File a bug report asking for a lightweight PlayOnLinux datastore access
       API to be created so they have the freedom to alter their on-disk format
       without breaking this.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import os, re
from .common import InstalledGameEntry, GameLauncher

BACKEND_NAME = "PlayOnLinux"
POL_PREFIX = os.path.expanduser('~/.PlayOnLinux')

# Let this get subbed in elsewhere so there's a clean way to identify which
# entries had to fall back to a default icon
DEFAULT_ICON = "playonlinux"

def humansort_key(strng):
    """Human/natural sort key-gathering function for sorted()
    Source: http://stackoverflow.com/a/1940105
    """
    if isinstance(strng, tuple):
        strng = strng[0]
    return [w.isdigit() and int(w) or w.lower()
            for w in re.split(r'(\d+)', strng)]

def get_games():
    """Retrieve a list of games installed in PlayOnLinux."""

    if not os.path.exists(POL_PREFIX):
        return []

    results = []
    for name in os.listdir(os.path.join(POL_PREFIX, 'shortcuts')):
        if os.path.isdir(name):
            continue

        # Skip DE-generated cruft
        if name in ['.desktop', '.DS_Store']:
            continue

        # Search the icon folders for a match in reverse human/natural sort
        # order (names like "scalable" and "full_size" first, followed by a
        # reverse numeric traversal from 256 down through to 16)
        icon, icon_prefix = None, os.path.join(POL_PREFIX, 'icones')
        for dname in sorted(os.listdir(icon_prefix),
                            key=humansort_key, reverse=True):
            dpath = os.path.join(icon_prefix, dname)
            icon_path = os.path.join(dpath, name)
            if os.path.isdir(dpath) and os.path.exists(icon_path):
                icon = icon_path
                break

        results.append(InstalledGameEntry(
            name=name,
            icon=icon,
            commands=[GameLauncher(
                argv=["playonlinux", "--run", name],
                provider=BACKEND_NAME,
                role=GameLauncher.Roles.play,
                name=name,
                icon=icon,
                use_terminal=False)
            ]))
    return results
