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


"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

import re, shlex
import xdg.Menu
from .common import GameEntry

# TODO: Include my patched xdg-terminal or some other fallback mechanism
TERMINAL_CMD = 'xterm -e %s'

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

            name = dentry.getName() or entry.DesktopFileID
            ico_name = dentry.getIcon()
            cmd = re.sub('%%', '%', re.sub('%[a-zA-Z]', '', dentry.getExec()))

            if dentry.getTerminal():
                cmd = TERMINAL_CMD % cmd

            entries.append((name.strip(), ico_name.strip(), cmd.strip(),
                            dentry))
        else:
            print("S: %s" % entry)

    return entries

def get_games(root_folder='Games'):
    """Retrieve a list of games from the XDG system menus.

    Written based on this public-domain code:
    http://mmoeller.fedorapeople.org/icewm/icewm-xdg-menu/icewm-xdg-menu

    @bug: On *buntu, this code doesn't find games unless you explicitly pass in
          the appropriate C{root_folder} value.
    """
    menu = xdg.Menu.parse()
    if root_folder:
        menu = menu.getMenu(root_folder)

    return [GameEntry(x[0], x[1], shlex.split(x[2]))
            for x in _process_menu(menu)]
