"""Sub-plugin to guess metadata if all else fails.

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
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import os, logging
from glob import glob

from ..common import GameLauncher
from ...util.icons import pick_icon
from ...util.naming import filename_to_name
from ...util.executables import Roles, classify_executable

# TODO: Finish moving icon-identifying code into ...util.icons
from ...util.icons import ICON_EXTS

# TODO: See if I can justify moving the use of this into ...util
from ...util.common import RESOURCE_DIRS_RE

BACKEND_NAME = "filesystem heuristics"
log = logging.getLogger(__name__)

def pathjoin_if(parent, child):
    """@todo: Decide whether this is the best way to do it."""
    return os.path.join(parent, child) if child else None

def find_files(path):
    """Wrapper around os.listdir() which returns +x files, icons, and subdirs.
    """
    executables = {}
    icons = []
    subdirs = []

    if not os.path.isdir(path):
        # TODO: Consider handling this
        return None

    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        fext = os.path.splitext(fname)[1].lower()
        if os.path.isdir(fpath):
            subdirs.append(fname)
        elif fext in ICON_EXTS:
            icons.append(fname)
        elif os.access(fpath, os.X_OK):
            etype = classify_executable(fname)
            if etype is not None:
                executables.setdefault(etype, []).append(fname)
    return {
        'executables': executables,
        'icons': icons,
        'subdirs': subdirs
    }

def inspect(path):
    """Try to guess metadata from the given folder"""
    name = filename_to_name(os.path.basename(path))
    found = find_files(path)

    if found:
        exes = found.get('executables', {})
        icons = found.get('icons', [])
        subdirs = found.get('subdirs', [])
    else:
        return None

    # TODO: Make this case-insensitive
    if not icons:
        icons += glob(os.path.join(
            path, "*_Data", "Resources", "UnityPlayer.png"))

        # TODO: Do this generally and properly
        icons += glob(os.path.join(
            path, "data", "icons", "*.ico"))

    if len(exes) > 1 and "run.sh" in exes:
        exes[:] = ['run.sh']

    # Find icons in asset subdirectories
    if len(icons) < 1:
        uncase_map = {x.lower(): x for x in subdirs}
        for subname in uncase_map:
            if RESOURCE_DIRS_RE.match(subname):
                subname_real = uncase_map[subname]
                subfound = find_files(os.path.join(path, subname_real))
                if subfound['icons']:
                    icons.extend([os.path.join(
                        subname_real, x) for x in subfound['icons']])

    icon = pick_icon(icons, path)
    result = {
        'name': name,
        'icon': icon,
        'provider': BACKEND_NAME,  # TODO: Allow this to be inferred
        'base_path': path,
        'commands': [],
    }

    if Roles.play in exes:
        result['commands'].extend(
            GameLauncher(name=x, icon=icon,
                         argv=[os.path.join(path, x)],
                         provider=BACKEND_NAME,
                         role=Roles.play)
            for x in exes[Roles.play])
    elif len(exes) == 1 and len(exes.values()[0]) == 1:
        # TODO: bit.trip.runner and Runner 2 have everything in a folder and
        #       only "install" and related files are at the top level. We'll
        #       need to detect and recurse somehow.
        #       (Also, it should be useful to scrape clues from un-installed
        #        .desktop files that are hard-coded to the install location)
        # TODO: Games like EufloriaHD also express a similar pattern but with
        #       the mojosetup uninstall stuff being the top-level thing.
        exe = exes.values()[0][0]
        result['commands'].append(
            GameLauncher(name=exe, icon=icon, argv=[os.path.join(path, exe)],
                         provider=BACKEND_NAME,
                         role=exes.keys()[0]))

    return result if result['commands'] else None

    # TODO: More testcases for filename_to_name

    # TODO:
    #       preferring
    #       names like play.sh, run.sh, rungame.sh, run-*.sh, etc.,
    #       and icon.*, recognizing the significance of names like uninstall*
    #       and install*, demoting names like extract-*,
    #       preferring Foo and Foo.sh over Foo.$ARCH
    #       and trying to prefer shallower paths to executables but
    #       preferring bin/ when descending is necessary
    if len(exes) > 1:
        print("TOO MANY EXE: %s" % exes)
    elif len(exes) < 0:
        print("NO EXE FOUND: %s" % path)
    elif len(icons) > 1:
        print("TOO MANY ICO: %s" % icons)
    elif len(icons) < 1:
        print("NO ICO FOUND: %s" % path)
    else:
        print("OTHER FAIL: %s = %r" % (path, found))

    return None
