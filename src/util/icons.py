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
)
NON_ICON_NAMES_RE = multiglob_compile(NON_ICON_NAMES, re_flags=re.I)

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

    # Prefer images with icon in the name as icons.
    result = []
    for icon in icons:
        if 'icon' in icon.lower():
            result.append(icon)
    icons = result or icons

    # Prefer images named icon.*
    result = []
    for icon in icons:
        significant = os.path.splitext(icon)[0].lower()
        if significant == 'icon':
            result.append(icon)
    icons = result or icons

    # TODO: Prefer square images so we don't wind up using Time Swap's Ouya
    #       icon by mistake.

    # TODO: Prefer SVG > PNG > XPM > BMP > JPEG
    #       (But try to find a way to prefer timeswapIcon.png over icon.svg
    #        without resorting to rendering the SVG and picking the one
    #        that's colour rather than sepia-toned grayscale)

    # TODO: Once I've got a regression suite in place, try capturing the
    #       NEO Scavenger icon by matching for img/*logo.*

    # TODO: Need to understand patterns like *_(32|128).png so SuperTuxKart
    #       reliably gets the bigger icon when it needs to be upscaled.

    # TODO: I'll need to extract icons from .exe files in Mono-based games
    #       like Atom Zombie Smasher which don't offer them separately.
    #       (Also, it should be possible to get additional cues as to a game's
    #        name by looking for binaries with the same spelling but different
    #        capitalization when the folder name is all lowercase)

    # TODO: If nothing else matches, look inside things like
    #       EndlessNuclearKittens.jar to find (16|32|64|128).png

    # TODO: Make this smarter
    return os.path.join(parent_path, icons[0])

# vim: set sw=4 sts=4 expandtab :
