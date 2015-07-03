"""Code to retrieve a list of installed games via the XDG menu system

Original Source: https://gist.github.com/ssokolow/1692707
Requires: PyXDG (python3-xdg on Debian-based distros)

Copyright (C) 2012-2014 Stephan Sokolow

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

BACKEND_NAME="XDG"

import logging, re
import xdg.Menu
from .common import InstalledGameEntry, GameLauncher, resolve_exec

log = logging.getLogger(__name__)

def _process_menu(menu):
    """Recursive handler for getting games from menus.

    Written based on this public-domain code by Konstantin Korikov:
    http://mmoeller.fedorapeople.org/icewm/icewm-xdg-menu/icewm-xdg-menu
    """
    entries = []
    for entry in menu.getEntries():
        if isinstance(entry, xdg.Menu.Menu):
            entries.extend(_process_menu(entry))
        elif isinstance(entry, xdg.Menu.MenuEntry):
            dentry = entry.DesktopEntry

            entries.append(dentry)
        else:
            log.debug("S: %s", entry)

    return entries

def get_games(root_folder='Games'):
    """Retrieve a list of games from the XDG system menus.

    Written based on this public-domain code:
    http://mmoeller.fedorapeople.org/icewm/icewm-xdg-menu/icewm-xdg-menu

    @bug: On *buntu, this code doesn't find games unless you explicitly pass in
          the appropriate C{root_folder} value.
    """
    results = []
    menu = xdg.Menu.parse()

    if root_folder:
        menu = menu.getMenu(root_folder)

    for dentry in _process_menu(menu):
        if (dentry.getType() != 'Application' or
                dentry.getNoDisplay() or
                dentry.getHidden()):  # TODO: allow ignoring Hidden?
            continue

        # Remove the placeholder tokens used in the Exec key
        # TODO: Actually sub in things like %i, %c, %k.
        # XXX: Should I centralize this substitution to allow argument passing?
        #      (eg. for Emulators?)
        cmd = re.sub('%[a-zA-Z]', '', dentry.getExec())

        name = (dentry.getName() or dentry.DesktopFileID).strip()
        icon = dentry.getIcon().strip()
        results.append(InstalledGameEntry(
            name=name,
            icon=icon,
            provider=BACKEND_NAME,
            commands=[GameLauncher(
                # Needed to work around Desura .desktop quoting failure
                argv=resolve_exec(cmd),
                provider=BACKEND_NAME,
                role=GameLauncher.Roles.play,
                name=name,
                path=dentry.getPath(),
                icon=icon,
                description=dentry.getComment(),
                tryexec=dentry.getTryExec(),
                xdg_categories=dentry.getCategories(),
                keywords=dentry.getKeywords(),
                use_terminal=dentry.getTerminal())
            ]))
    return results
