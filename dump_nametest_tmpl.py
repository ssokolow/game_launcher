#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple helper to reduce the drudgery of adding new cases to a
filename_to_name test corpus."""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "[application name here]"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import json, logging, os, sys
log = logging.getLogger(__name__)

from src.util.naming import filename_to_name

if sys.version_info.major > 2:
    basestring = str  # pylint: disable=redefined-builtin,invalid-name

def make_test_defs(acceptable):
    """Code shared between process_folder and --migrate"""
    if isinstance(acceptable, basestring):
        acceptable = [acceptable]

    return {
        'ideal': acceptable[0],
        'acceptable': acceptable,
        'MUST_AUDIT': True,
    }

# TODO: See if it's feasible to unify this code with the actual walker.
def process_folder(path):
    """Generate a mapping dict from filename_to_name suitable for the tests.

    To make each entry usable:
        1. Manually audit the results
        2. Remove the duplicate in 'acceptable' if 'ideal' needed no changes
        3. Remove the 'MUST_AUDIT' keyvalue pair.
    (Hand-edit it and merge it into the unit test's data.)
    """
    return {x: make_test_defs(filename_to_name(x))
            for x in os.listdir(path)
            if not x.startswith('.')}

def merge(existing, updates):
    """Merge new content into an existing entry but don't allow un-audited
    entries to overwrite audited ones."""
    for key, value in updates.items():
        if not key in existing or existing[key].get('MUST_AUDIT', False):
            existing[key] = value

def main():
    """The main entry point, compatible with setuptools entry points."""
    # If we're running on Python 2, take responsibility for preventing
    # output from causing UnicodeEncodeErrors. (Done here so it should only
    # happen when not being imported by some other program.)
    import sys
    if sys.version_info.major < 3:
        reload(sys)
        sys.setdefaultencoding('utf-8')  # pylint: disable=no-member

    from argparse import ArgumentParser, RawTextHelpFormatter
    parser = ArgumentParser(
        description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_argument('--version', action='version',
        version="%%(prog)s v%s" % __version__)
    parser.add_argument('-v', '--verbose', action="count",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_argument('-q', '--quiet', action="count",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    parser.add_argument('--update', action="append", dest="update", default=[],
        help="Specify an existing file to be overlaid on the results. "
             "(Existing hand-audited entries will not be replaced)")
    parser.add_argument('--migrate', action="store_true", dest="migrate",
        default=False, help="Migrate the hard-coded keys from an early version"
        " of the test suite.")
    parser.add_argument('input_paths', nargs='+', metavar='PATH',
        help="Path of a directory containing source file/directory names")

    args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose - args.quiet, len(log_levels) - 1)
    args.verbose = max(args.verbose, 0)
    logging.basicConfig(level=log_levels[args.verbose],
                        format='%(levelname)s: %(message)s')

    accum = {}

    if args.migrate:
        from test.util.test_naming import filename_test_map
        merge(accum, {x: make_test_defs(y)
                      for x, y in filename_test_map.items()})

    for path in args.update:
        with open(path, 'rU') as fobj:
            merge(accum, json.load(fobj))

    for path in args.input_paths:
        merge(accum, process_folder(path))

    print(json.dumps(accum, indent=2))

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
