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
from ...util.common import multiglob_compile
from ...util.naming import filename_to_name
from ..common import InstalledGameEntry

from . import gog, ssokolow_install_sh, guesser

# Placeholders for user-specified values which should be stored in the database
# TODO: Some kind of "If it's in /usr/games, default to Terminal=true" rule
GAMES_DIRS = ['/mnt/buffalo_ext/games', os.path.expanduser('~/opt'),
              '/usr/games']
BLACKLIST = [
    '*/teensyduino.old',
    '*/fennec-10.0.0.2',
    '*/Opera_Mobile_Emulator',
    '*/firefox',  # TODO: Include */firefox[_-]*
]

# Files which shouldn't require +x to be considered for inclusion
# (SWF really doesn't need +x while top-level -x JAR files should be noticed)
EXEC_EXCEPTIONS = ('.swf', '.jar')

log = logging.getLogger(__name__)

def gather_candidates(path, blacklist=BLACKLIST):  # pylint: disable=W0102
    """C{os.listdir()} the contents of a folder and filter for potential games.

    This is essentially a pre-filter to eliminate things which cannot be games
    as quickly and in as lightweight a manner as possible.
    """
    blacklist_re = multiglob_compile(blacklist, prefix=True)
    candidates = set()
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
            log.debug("Directories are automatically accepted: %s", fpath)
            candidates.add(fpath)
            continue

        # Skip non-executable files that need +x to be potential games
        if not os.access(fpath, os.X_OK):
            if not os.path.splitext(fpath)[1].lower() in EXEC_EXCEPTIONS:
                continue

        candidates.add(fpath)
    return candidates

def get_games(roots=GAMES_DIRS):  # pylint: disable=dangerous-default-value
    """List potential games by examining a set of /opt-like paths."""
    candidates = set()
    # TODO: Do some symlink resolution and path deduplication on roots here

    for root in roots:
        candidates.update(gather_candidates(root))

    results = []
    for candidate in candidates:
        for subplugin in (gog, ssokolow_install_sh, guesser):
            result = subplugin.inspect(candidate)
            if result:
                results.append(InstalledGameEntry(**result))
                break
        else:
            log.info("Fallback - <Unmatched>: %s",
                     filename_to_name(os.path.basename(candidate)))

    # TODO: Another sub-plugin to be called after the GOG and install.sh ones
    #       which feels around for .desktop files and executable binaries.
    #       (But only once I've decided how to implement a priority order so
    #        it doesn'r clutter things up with the guts of stuff also found by
    #        other backends like the XDG menu one.)

    return results
