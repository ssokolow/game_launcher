"""Routines for finding and classifying a game's executables"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import enum, os, re
from .common import multiglob_compile

# Files which shouldn't be considered as executables even when marked +x
NON_BINARY_EXTS = (
    '.dll', '.so', '.dso', '.shlib', '.o', '.dylib'
    '.ini', '.xml', '.txt',
    '.assets', '.u', '.frag', '.vert', '.fxg', '.xnb', '.xsb', '.xwb', '.xgs',
    '.usf', '.msf', '.asi', '.fsb', '.fev', '.mdd', '.lbx', '.zmp',
    '.as', '.cpp', '.c', '.h', '.java',
    '.ogg', '.mp3', '.wav', '.spc', '.mid', '.midi', '.rmi',
    '.png', '.bmp', '.gif', '.jpg', '.jpeg', '.svg', '.tga', '.pcx',
    '.pdf',
    '.ttf', '.crt',
    '.dl_', '.sc_', '.ex_',
)
# .mojosetup/*, uninstall-*, java/, node_modules, xdg-*, Shaders, *~, Mono
NON_BINARY_EXTS_RE = multiglob_compile(NON_BINARY_EXTS, re_flags=re.I)

IGNORED_BINARIES = (
    'xdg-*', 'flashplayer',
    'Data.*',
    'lib*.so.*',
    'README*',
)
IGNORED_BINARIES_RE = multiglob_compile(IGNORED_BINARIES, re_flags=re.I)

def classify_executable(fname):
    """High-level wrapper for Roles.guess() which supports ignoring files."""
    fname_pat, fext = os.path.splitext(fname)
    fname_pat = fname_pat.lower()
    if NON_BINARY_EXTS_RE.match(fext) or IGNORED_BINARIES_RE.match(fname):
        return None
    return Roles.guess(fname)

@enum.unique  # pylint: disable=too-few-public-methods
class Roles(enum.IntEnum):
    """An enumeration of the roles L{GameSubentry} instances can take.

    @note: These values should be maintained in an order that allows them
           to be used as keys to sort launchers from most to least safe to
           run.

    @note: The intended use of these is as follows:
        1. Use provider metadata to clearly identify roles when available.
        2. Use L{Roles.guess} to separate out configuration, installation,
           and uninstallation commands.
        3. Use C{play} as a fallback value and then determine the most
           likely candidate for the primary launcher command.
        4. Reassign all remaining C{play} commands to C{unknown} if
           affirmative evidence of that role isn't available.
    """

    # We want bool(unknown) == False but we also want this sort order.
    play = -2
    configure = -1
    unknown = 0
    install = 1
    uninstall = 2

    @classmethod
    def guess(cls, name):
        """Guess the role of a command from its title or filename"""
        if name:
            name = name.lower()

            # Used to ensure a misclassification is as failsafe as possible
            # (By making ambiguous executables resolve to the scarier label)
            resolution_order = [
                cls.uninstall,
                cls.install,
                cls.configure,
                cls.play
            ]

            # Used to identify classifications based on filename substrings
            mappings = {
                cls.play: ('run', 'play', 'start', 'game', 'launcher',
                           'addon', 'client', 'server'),
                cls.configure: ('config', 'setup', 'settings'),
                cls.install: ('install', 'extract', 'unpack'),
                cls.uninstall: ('uninst', 'remove'),
            }

            for key in resolution_order:
                for fragment in mappings[key]:
                    if fragment in name:
                        return key
        return cls.unknown

# vim: set sw=4 sts=4 expandtab :
