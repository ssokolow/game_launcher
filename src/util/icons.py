"""Routines for finding a game's icon"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import os, re
from .common import multiglob_compile

# Files which should be heuristically considered to identify a program's icon
ICON_EXTS = (
    '.png', '.xpm',
    '.svg', '.svgz', '.svg.gz',
    '.jpg', '.jpe', '.jpeg',
    '.bmp', '.ico',
)

NON_ICON_NAMES = (
    '*background*', 'bg*',
    'character*',
    'sheet*',
    'tile*',
    # TODO: Should really be regex'd with \d* to be less case-specific
    'items.*',
    'terrain.*',
)
NON_ICON_NAMES_RE = multiglob_compile(NON_ICON_NAMES, re_flags=re.I)


# TODO: Is there a way to inject an icon into Qt's icon store similar to
#       gtk_icon_theme_add_builtin_icon so I don't have to reimplement the
#       process of loading different icons as the widget's scaling properties
#       are changed?
# TODO: Rework the internals of this once I've got it actually functional
class BaseIconWrapper(object):

    """

    def __init__(self, raw_obj):
        self._raw = raw_obj



    def unwrap(self):
        """Return the raw toolkit object being wrapped."""
        return self._raw

def calculate_icon_score(filename):
    # TODO: Prefer square images so we don't wind up using Time Swap's Ouya
    #       icon by mistake.

    # TODO: Once I've got a regression suite in place, try capturing the
    #       NEO Scavenger icon by matching for img/*logo.*

    # TODO: I'll need to extract icons from .exe files in Mono-based games
    #       like Atom Zombie Smasher which don't offer them separately.
    #       (Also, it should be possible to get additional cues as to a game's
    #        name by looking for binaries with the same spelling but different
    #        capitalization when the folder name is all lowercase)

    # TODO: If nothing else matches, look inside things like
    #       EndlessNuclearKittens.jar to find (16|32|64|128).png

    # TODO: Try to find a way to prefer timeswapIcon.png over icon.svg
    #        without resorting to rendering the SVG and picking the one
    #        that's colour rather than sepia-toned grayscale.
    formats = {
        '.svg': 5,
        '.png': 4,
        '.xpm': 3,
        '.bmp': 2,
        '.jpg': 1,
    }

    base, ext = [x.lower() for x in os.path.splitext(filename)]
    score = (
        formats.get(ext, 0) +
        (2 if 'icon' in base else 0) +
        (2 if base == 'icon' else 0) +
        (-1 if filename.startswith('.') else 0)
    )
    # Return a sorting key consisting of the score and a cheap approximation
    # of parsing out things like `128x128` and picking the largest.
    return (score, int(''.join(s for s in base if s.isdigit()) or 0))


def pick_icon(icons, parent_path):
    """Choose the best icon from a set of detected image files.

    @todo: Maybe redesign this on a score-based system?
    @todo: Support multiple sizes
    @todo: Return a fallback list so a failed load can fall back.

    @todo: Write a unit test suite as I did for the name guesser.
    """
    if not icons:
        return None

    # Ignore non-icon resources
    result = []
    for img in icons:
        if not NON_ICON_NAMES_RE.match(img):
            result.append(img)
    icons = result or icons
    icons.sort(key=calculate_icon_score, reverse=True)


    # TODO: Make this smarter
    return os.path.join(parent_path, icons[0])

# vim: set sw=4 sts=4 expandtab :
