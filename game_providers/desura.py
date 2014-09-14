"""Code to retrieve a list of installed games from the Desura client

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

import os, shlex, sqlite3
from .common import InstalledGameEntry

DESURA_DB = os.path.expanduser('~/.desura/iteminfo_d.sqlite')

def get_games():
    """Retrieve a list of games from the Desura client's data store.

    @todo: Support all Desura dotfile configurations rather than just the
        one my system happens to use.
    """

    if not os.path.exists(DESURA_DB):
        return []

    conn = sqlite3.connect(DESURA_DB)
    results = []
    for row in conn.execute("""SELECT DISTINCT
            i.internalid, i.name, e.name, i.icon,
            e.exe, e.exeargs, e.userargs
            FROM iteminfo AS i, exe AS e
            WHERE i.internalid = e.itemid"""):

        argv = [row[4]] + shlex.split(row[5]) + shlex.split(row[6])
        if row[2] == 'Play':
            name = row[1]
        else:
            name = '%s - %s' % (row[1], row[2])

        # TODO: Rework this once I have sub-entry support.
        # (including using things like for desura_launch_Play.sh)
        results.append(InstalledGameEntry(name=name, icon=row[3], argv=argv))
    return results
