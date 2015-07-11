"""Code to retrieve a list of installed games from PlayOnLinux

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
from ..util.executables import Roles
from ..util.shlexing import lex_shellscript, make_metadata_mapper

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

# TODO: There should be a way for a scraper to suppress entries like the
#       PlayOnLinux XDG launcher from appearing and, instead, expose it
#       somewhere else (the context menu, maybe?)
def get_games():
    """Retrieve a list of games installed in PlayOnLinux."""

    if not os.path.exists(POL_PREFIX):
        return []

    results = []
    shortcut_dir = os.path.join(POL_PREFIX, 'shortcuts')
    for name in os.listdir(shortcut_dir):
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

        fields = lex_shellscript(os.path.join(shortcut_dir, name),
            make_metadata_mapper({'WINEPREFIX': 'base_path'}))
        if 'base_path' not in fields:
            print(os.path.join(shortcut_dir, name), fields)
            continue

        # TODO: Find the original source icons in the WINEPREFIXes to work
        #       around PlayOnLinux's sub-par rescaling. Affects:
        #        - Delve Deeper
        #        - Gnomoria
        #        - Heart of Darkness
        #        - Lemmings for Windows
        #        - Lode Runner Online: The Mad Monks' Revenge
        #        - Megabyte Punch
        #        - Perfect Cherry Blossom
        #        - Prince of Persia: The Sands of Time
        #        - Rayman Origins

        # TODO: Come up with an API to indicate to the parent app that
        #       the PlayOnLinux entry should be moved from the main listing to
        #       a menu (either context or otherwise) if this successfully
        #       finds games.

        results.append(InstalledGameEntry(
            name=name,
            icon=icon,
            base_path=fields['base_path'],
            commands=[GameLauncher(
                argv=["playonlinux", "--run", name],
                provider=BACKEND_NAME,
                role=Roles.guess(name),
                name=name,
                icon=icon,
                use_terminal=False)
            ]))
    return results
