"""Code to retrieve a list of installed games from the Desura client

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

import os, shlex, sqlite3
from ..util.executables import Roles
from .common import InstalledGameEntry, GameLauncher

DESURA_DB = os.path.expanduser('~/.desura/iteminfo_d.sqlite')
BACKEND_NAME = "Desura"

def get_games():
    """Retrieve a list of games from the Desura client's data store.

    @todo: Support all Desura dotfile configurations rather than just the
        one my system happens to use.
    """

    if not os.path.exists(DESURA_DB):
        return []

    conn = sqlite3.connect(DESURA_DB)
    entries = {}
    for row in conn.execute("""SELECT DISTINCT
            i.internalid, i.name, e.name, i.icon,
            e.exe, e.exeargs, e.userargs, ii.installcheck,
            i.developer, i.publisher, ii.installpath
            FROM iteminfo AS i, exe AS e, installinfo as ii
            WHERE i.internalid = e.itemid AND i.internalid = ii.itemid
            ORDER BY e.rank ASC"""):

        if row[2].lower().startswith('play'):
            role = Roles.play
        elif row[2].lower().startswith('settings'):
            role = Roles.configure
        else:
            role = Roles.unknown

        if row[0] not in entries:
            entries[row[0]] = InstalledGameEntry(name=row[1], icon=row[3],
                                                 base_path=row[10])

        # TODO: Inspect base_path to see if the game has a higher-resolution
        #       icon than Desura's cached version.
        #       (Crayon Physics, Darwinia, Frozen Synapse, Trine, World of Goo)
        #       (I'll probably need some kind of confidence value in the icon
        #        detector's result so Desura can override low-confidence
        #        responses. In fact, that'd probably be a good way to handle
        #        priority in deduplication in general.)

        # TODO: Come up with an API to indicate to the parent app that
        #       Desura/Desurium entries should be moved from the main listing
        #       to a menu (either context or otherwise) if this successfully
        #       finds games.

        # TODO: Maybe something which writes a desura_icon.png into the game
        #       folder if it fails to find any icon there?

        entries[row[0]].commands.append(GameLauncher(
                argv=[row[4]] + shlex.split(row[5]) + shlex.split(row[6]),
                provider=BACKEND_NAME,
                role=role,
                name=row[2],
                icon=row[3],
                description="Developer: %s\nPublisher: %s" % (row[8], row[9]),
                tryexec=row[7],
                use_terminal=False))
    return entries.values()
