"""Routines and data common to multiple utility domains"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import fnmatch, os, re, shlex, sys

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
    return [w.isdigit() and int(w) or w.lower()
            for w in re.split(r'(\d+)', strng)]

def which(exec_name, execpath=None):
    """Like the UNIX which command, this function attempts to find the given
    executable in the system's search path. Returns C{None} if it cannot find
    anything.

    @todo: Find the copy I extended with win32all and use it here.
    @todo: Figure out how to "pragma: no cover" conditional on os.name.
    """
    if 'nt' in os.name:
        def test(path):
            """@todo: Is there a more thorough way to do this on Windows?"""
            return os.path.exists(path)

        # TODO: Figure out how to retrieve this list from the OS.
        # (We can't just use PATHEXT according to
        #  http://bugs.python.org/issue2200#msg131532 because spawnv doesn't
        #  support all extensions)
        suffixes = ['.exe', '.com', '.bat', '.cmd']  # pragma: no cover
    else:
        def test(path):
            """@todo: Is there a more thorough way to check this?"""
            return os.access(path, os.X_OK)
        suffixes = []

    if isinstance(execpath, basestring):
        execpath = execpath.split(os.pathsep)
    elif not execpath:
        execpath = os.environ.get('PATH', os.defpath).split(os.pathsep)

    for path in execpath:
        full_path = os.path.join(os.path.expanduser(path), exec_name)
        if test(full_path):
            return full_path
        for suffix in suffixes:
            if test(full_path + suffix):  # pragma: no cover
                return full_path + suffix
    return None  # Couldn't find anything.

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
