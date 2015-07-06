#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""[application description here]"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "[application name here]"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import json, logging, os
log = logging.getLogger(__name__)

from src.util.naming import filename_to_name

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
            for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))}

def merge(existing, updates):
    """Merge new content into an existing entry but don't allow un-audited
    entries to overwrite audited ones."""
    for key, value in updates.items():
        if not key in existing or existing[key].get('MUST_AUDIT', False):
            existing[key] = value

def main():
    """The main entry point, compatible with setuptools entry points."""
    from optparse import OptionParser
    parser = OptionParser(version="%%prog v%s" % __version__,
            usage="%prog [options] <argument> ...",
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_option('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_option('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    parser.add_option('--update', action="append", dest="update",
        help="Specify an existing file to be overlaid on the results. "
             "(Existing hand-audited entries will not be replaced)")
    parser.add_option('--migrate', action="store_true", dest="migrate",
        default=False, help="Migrate the hard-coded keys from an early version"
        " of the test suite.")

    # Allow pre-formatted descriptions
    parser.formatter.format_description = lambda description: description

    opts, args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    opts.verbose = min(opts.verbose - opts.quiet, len(log_levels) - 1)
    opts.verbose = max(opts.verbose, 0)
    logging.basicConfig(level=log_levels[opts.verbose],
                        format='%(levelname)s: %(message)s')

    accum = {}

    if opts.migrate:
        from test.util.test_naming import filename_test_map
        merge(accum, {x: make_test_defs(y)
                      for x, y in filename_test_map.items()})

    for path in opts.update:
        with open(path, 'rU') as fobj:
            merge(accum, json.load(fobj))

    for path in args:
        merge(accum, process_folder(path))

    print(json.dumps(accum, indent=2))

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
