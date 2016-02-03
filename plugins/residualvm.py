"""Code to retrieve a list of installed games from ResidualVM

Copyright (C) 2015 Stephan Sokolow

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

@todo: File a bug report asking for a way to request a game's path without
       manually parsing .residualvmrc
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import logging, os, subprocess

# TODO: Decide on a name for the program and rename "src"
from src import interfaces
from src.game_providers.common import InstalledGameEntry, GameLauncher
from src.util.executables import Roles

try:                 # Python 3.x
    from configparser import RawConfigParser
    from configparser import Error as CP_Error  # pylint: disable=E0611
except ImportError:  # Python 2.x
    from ConfigParser import RawConfigParser
    from ConfigParser import Error as CP_Error

from xdg.IconTheme import getIconPath

RC_PATH = os.path.expanduser('~/.residualvmrc')

log = logging.getLogger(__name__)

class ResidualVMProvider(interfaces.IGameProvider):
    backend_name = "ResidualVM"
    default_icon = getIconPath("residualvm", 128)

    @staticmethod
    def _parse_list(args):
        """Parse C{residualvm --list-targets} for a list of available games"""
        try:
            rows = subprocess.check_output(['residualvm'] + args)

            if isinstance(rows, bytes):
                rows = rows.decode('utf-8')

            rows = rows.strip().split('\n')[2:]

            result = {}
            for row in rows:
                game_id, name = row.split(None, 1)
                result[game_id.strip()] = name.strip()
            return result

        except subprocess.CalledProcessError:
            log.info("Could not retrieve list of games from ScummVM")
            return {}

    # TODO: There should be a way for a scraper to suppress entries like
    #       ResidualVM itself and, instead, expose it somewhere else
    #       (context menu, maybe?)
    def get_games(self):
        """Retrieve a list of games configured for play via ResidualVM."""
        if not os.path.exists(RC_PATH):
            log.info("Could not find ResidualVM RC file at %s", RC_PATH)
            return {}  # TODO: Do I really NEED base_path?

        try:
            rc_parser = RawConfigParser()
            rc_parser.read(RC_PATH)
        except CP_Error as err:
            log.error("Could not parse ResidualVM RC file: %s", err)

        results = []
        for game_id, name in self._parse_list(['--list-targets']).items():
            game_id, name = game_id.strip(), name.strip()

            try:
                base_path = rc_parser.get(game_id, 'path')
            except CP_Error as err:
                log.error("Error attempting to get base path for %s: %s",
                          game_id, err)
                # TODO: Do I really NEED base_path?
                continue

            # TODO: Look for an icon (Also, Recognize GOG games being used as a
            #       data source for the system ResidualVM and reset the base
            #       path one level up)

            # TODO: Deduplicate based on .get(game_id, 'gameid') once I figure
            # out how to make sure that things like gameid=sci don't cause
            # false positives. (Common name prefix won't be enough because of
            # things like the King's Quest series. Maybe name sans brackets?)

            # TODO: Consider integrating scraping sufficient to allow launching
            #       directly into a save file via the context menu.

            results.append(InstalledGameEntry(
                name=name,
                icon=self.default_icon,
                base_path=base_path,
                commands=[GameLauncher(
                    argv=["residualvm", game_id],
                    provider=self.backend_name,
                    role=Roles.play,
                    name=name,
                    icon=self.default_icon,
                    use_terminal=False)
                ]))
        return results
