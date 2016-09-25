"""Code to attempt to build a list of games by walking the filesystem.

(Named "fallback" because the inherent imprecision relegates it to filling in
the gaps left by the better approaches.)

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

@todo: Some kind of (path, size, ctime)-backed analogue to If-Modified-Since
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import logging, os
from src import interfaces
from src.util.common import multiglob_compile
from src.util.naming import filename_to_name

BLACKLIST = [
    '*/teensyduino.old',
    '*/fennec-*',  # TODO: Match only version numbers
    '*/Opera_Mobile_Emulator',
    '*/firefox',  # TODO: Include */firefox[_-]*
]

# Files which shouldn't require +x to be considered for inclusion
# (SWF really doesn't need +x while top-level -x JAR files should be noticed)
EXEC_EXCEPTIONS = ('.swf', '.jar')

log = logging.getLogger(__name__)

class FallbackProvider(interfaces.IGameProvider):
    precedence = interfaces.Precedence.lowest
    backend_name = "Fallback"

    @staticmethod
    def get_games_dirs():
        """Abstraction for retrieving the user's list of game folders."""
        # TODO: Is it worth it to return a sorted list?
        return set(os.path.abspath(x) for x in interfaces.GAMES_DIRS)

    @staticmethod
    def gather_candidates(path, blacklist=BLACKLIST):  # pylint: disable=W0102
        """C{os.listdir()} contents of a folder and filter for likely games.

        This is essentially a pre-filter to eliminate things which cannot be
        games as quickly and in as lightweight a manner as possible.
        """
        candidates = set()
        if not os.path.isdir(path):
            return candidates

        blacklist_re = multiglob_compile(blacklist, prefix=True)
        for fname in os.listdir(path):
            fpath = os.path.join(path, fname)

            # Skip hidden files and directories
            if fname.startswith('.'):
                log.debug("Skipped hidden file/folder: %s", fpath)
                continue

            # Skip blacklisted paths
            if blacklist_re.match(fpath):
                log.debug("Skipped blacklisted path: %s", fpath)
                continue

            # Directories get a free pass to stage two
            if os.path.isdir(fpath):
                #log.debug("Directories are automatically accepted: %s", fpath)
                candidates.add(fpath)
                continue

            # Skip non-executable files that need +x to be potential games
            if not os.access(fpath, os.X_OK):
                if not os.path.splitext(fpath)[1].lower() in EXEC_EXCEPTIONS:
                    continue

            candidates.add(fpath)
        return candidates

    @staticmethod
    def inspect_candidate(path):
        """Try to generate a metadata entry from a path"""
        for subplugin in interfaces.IFallbackGameProvider.get_all():
            result = subplugin.inspect(path)
            if result:
                try:
                    return interfaces.InstalledGameEntry(**result)
                except TypeError:
                    print("TypeError for InstalledGameEntry(**%r)" % result)
                    raise
                break
        else:
            log.info("Fallback - <Unmatched>: %s",
                     filename_to_name(os.path.basename(path)))
            return None

    def get_games(self, roots=None):  # pylint: disable=dangerous-default-value
        """List potential games by examining a set of /opt-like paths."""
        candidates = set()
        roots = roots or self.get_games_dirs()
        for root in roots:
            candidates.update(self.gather_candidates(root))

        # pylint: disable=bad-builtin
        return list(filter(None, (self.inspect_candidate(path) for
                                  path in candidates)))
