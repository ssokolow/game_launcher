"""Code to retrieve a list of installed games via the XDG menu system

Original Source: https://gist.github.com/ssokolow/1692707
Requires: PyXDG (python3-xdg on Debian-based distros)

Copyright (C) 2012-2015 Stephan Sokolow

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

Relevant Reference:
- http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import logging, os, re
import xdg.Menu
from xdg.IconTheme import getIconPath

# TODO: Decide on a name for the program and rename "src"
from src import interfaces
from src.util.common import resolve_exec, which
from src.util.executables import Roles

log = logging.getLogger(__name__)

# TODO: Put this somewhere like util.common
# A list of paths that, if exactly matched, should not be used for game
# deduplication via install directory
COMMON_DIRS = [
    '/opt', os.path.expanduser('~/opt'),
    '/bin', os.path.expanduser('~/bin'),
    '/usr/games/bin', '/usr/local/games/bin',
    '/usr/games', '/usr/local/games',
    '/usr/bin', '/usr/local/bin',
]

class XDGMenuProvider(interfaces.IGameProvider):
    precedence = interfaces.Precedence.highest
    backend_name = "XDG"

    def _process_menu(self, menu):
        """Recursive handler for getting games from menus.

        Written based on this public-domain code by Konstantin Korikov:
        http://mmoeller.fedorapeople.org/icewm/icewm-xdg-menu/icewm-xdg-menu
        """
        entries = []
        for entry in menu.getEntries():
            if isinstance(entry, xdg.Menu.Menu):
                entries.extend(self._process_menu(entry))
            elif isinstance(entry, xdg.Menu.MenuEntry):
                dentry = entry.DesktopEntry

                entries.append(dentry)
            else:
                log.debug("S: %s", entry)

        return entries

    def get_games(self, root_folder='Games'):
        """Retrieve a list of games from the XDG system menus.

        Written based on this public-domain code:
        http://mmoeller.fedorapeople.org/icewm/icewm-xdg-menu/icewm-xdg-menu

        @bug: On *buntu, this code doesn't find games unless you explicitly
              pass in the appropriate C{root_folder} value.
        """
        results = []
        menu = xdg.Menu.parse()

        if root_folder:
            menu = menu.getMenu(root_folder)

        for dentry in self._process_menu(menu):
            if (dentry.getType() != 'Application' or
                    dentry.getNoDisplay() or
                    dentry.getHidden()):  # TODO: allow ignoring Hidden?
                continue

            # Remove the placeholder tokens used in the Exec key
            # TODO: Actually sub in things like %i, %c, %k.
            # XXX: Should I centralize this subbing to allow argument passing?
            #      (eg. for Emulators?)
            cmd = re.sub('%[a-zA-Z]', '', dentry.getExec())

            # TODO: Find a way to hint that one of copy of this is generated
            # TODO: Find a better way to let frontends ask for a specific size.
            name = (dentry.getName() or dentry.DesktopFileID).strip()
            icon = getIconPath((dentry.getIcon() or '').strip(), 128)
            path = dentry.getPath()

            # Replicate the findTryExec() method on pre-0.26 PyXDG versions
            # TODO: Audit uses elsewhere and then guarantee that
            # GameLauncher.tryexec will be a path or None
            tryexec = dentry.getTryExec()
            tryexec = which(tryexec) if tryexec else None

            # resolve_cmd needed to work around Desura .desktop quoting bug
            argv = resolve_exec(cmd)

            base_path = path or os.path.dirname(tryexec or argv[0]) or None
            if base_path and base_path in COMMON_DIRS:
                base_path = None

            # TODO: Rework
            results.append(interfaces.InstalledGameEntry(
                name=name,
                icon=icon,
                base_path=base_path,
                commands=[interfaces.GameLauncher(
                    argv=argv,
                    provider=self,
                    role=Roles.play,
                    name=name,
                    path=path,
                    icon=icon,
                    description=dentry.getComment(),
                    tryexec=tryexec,
                    categories=dentry.getCategories(),
                    keywords=dentry.getKeywords(),
                    use_terminal=dentry.getTerminal())
                ]))
        return results
