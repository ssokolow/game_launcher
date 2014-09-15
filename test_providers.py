#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Experimental code to drive and develop game providers

Copyright (C) 2014 Stephan Sokolow

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

@todo: Include a "help me refine the design" option which allows users to OK
       the submission of directory listings and contents of files like
       "start.sh" so I can debug cases of incomplete metadata collection.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Test code to drive game providers"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import logging
log = logging.getLogger(__name__)

from itertools import chain
from game_providers import xdg_menu, desura, playonlinux, fallback

def get_games():
    # TODO: Move priority ordering control into backend metadata
    games = sorted(chain(*[x.get_games() for x in (
        xdg_menu, desura, playonlinux, fallback)]))

    for entry in games[:]:
        if not entry.is_installed():
            log.info("Skipping entry from %s. Not installed: %s",
                     entry.provider, entry.argv)
            games.remove(entry)

    # TODO: Dedupe
    print('\n'.join(repr(x) for x in games))
    print("%d games found" % len(games))

def main():
    """The main entry point, compatible with setuptools entry points."""
    # pylint: disable=bad-continuation
    from optparse import OptionParser
    parser = OptionParser(version="%%prog v%s" % __version__,
            usage="%prog [options] <argument> ...",
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_option('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_option('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    # Reminder: %default can be used in help strings.

    # Allow pre-formatted descriptions
    parser.formatter.format_description = lambda description: description

    opts, _ = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    opts.verbose = min(opts.verbose - opts.quiet, len(log_levels) - 1)
    opts.verbose = max(opts.verbose, 0)
    logging.basicConfig(level=log_levels[opts.verbose],
                        format='%(levelname)s: %(message)s')

    get_games()

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
