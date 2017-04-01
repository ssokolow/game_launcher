"""Routines and data common to multiple utility domains"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import fnmatch, os, re, shlex, sys
from distutils.spawn import find_executable as which

RESOURCE_DIRS = (
    'assets',
    'data', '*_data',
    'resources',
    'icons',
)

# Ensure cmp is available to Python 3 for cases where it's the cleanest option
if sys.version_info.major >= 3:
    def cmp(i, j):  # pylint: disable=redefined-builtin
        """Thanks to http://python3porting.com/differences.html"""
        return (i > j) - (i < j)

    # Python 2+3 compatibility for isinstance()
    basestring = str  # pylint: disable=invalid-name,redefined-builtin
else:
    cmp = cmp  # Ensure that cmp is importable as a member of this module

def humansort_key(strng):
    """Human/natural sort key-gathering function for sorted()
    Source: http://stackoverflow.com/a/1940105
    """
    if isinstance(strng, tuple):
        strng = strng[0]
    return [int(w) if w.isdigit() else w.lower()
            for w in re.split(r'(\d+)', strng)]

def resolve_exec(cmd, rel_to=None):
    """Disambiguate spaces in a string which may or may not be shell-quoted"""
    split_cmd = shlex.split(cmd)

    if rel_to:
        cmd = os.path.join(rel_to, cmd)
        split_cmd[0] = os.path.join(rel_to, split_cmd[0])

    return split_cmd if (which(split_cmd[0]) and not which(cmd)) else [cmd]

def multiglob_compile(globs, prefix=False, re_flags=0):
    """Generate a single "A or B or C" regex from a list of shell globs.

    :param globs: Patterns to be processed by :mod:`fnmatch`.
    :type globs: iterable of :class:`~__builtins__.str`

    :param prefix: If ``True``, then :meth:`~re.RegexObject.match` will
        perform prefix matching rather than exact string matching.
    :type prefix: :class:`~__builtins__.bool`

    :rtype: :class:`re.RegexObject`
    """
    if not globs:
        # An empty globs list should only match empty strings
        return re.compile('^$')
    elif prefix:
        globs = [x + '*' for x in globs]
    return re.compile('|'.join(fnmatch.translate(x) for x in globs), re_flags)

RESOURCE_DIRS_RE = multiglob_compile(RESOURCE_DIRS, re_flags=re.I)

# vim: set sw=4 sts=4 expandtab :
