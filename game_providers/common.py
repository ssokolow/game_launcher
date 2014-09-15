from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

import logging, os, shlex
from functools import total_ordering

# TODO: Include my patched xdg-terminal or some other fallback mechanism
TERMINAL_CMD = ['xterm', '-e']

# Don't search for metadata inside scripts like "start.sh" if they're bigger
# than this size.
MAX_SCRIPT_SIZE = 1024 ** 2  # 1 MiB

# Python 2+3 compatibility for isinstance()
try:
    basestring
except NameError:
    basestring = str  # pylint: disable=invalid-name,redefined-builtin

log = logging.getLogger(__name__)

def which(exec_name, execpath=None):
    """Like the UNIX which command, this function attempts to find the given
    executable in the system's search path. Returns C{None} if it cannot find
    anything.

    @todo: Find the copy I extended with win32all and use it here.
    @todo: Figure out how to "pragma: no cover" conditional on os.name.
    """
    if 'nt' in os.name:
        # TODO: Figure out how to retrieve this list from the OS.
        # (We can't just use PATHEXT according to
        #  http://bugs.python.org/issue2200#msg131532 because spawnv doesn't
        #  support all extensions)
        suffixes = ['.exe', '.com', '.bat', '.cmd']  # pragma: no cover
    else:
        suffixes = []

    if isinstance(execpath, basestring):
        execpath = execpath.split(os.pathsep)
    elif not execpath:
        execpath = os.environ.get('PATH', os.defpath).split(os.pathsep)

    for path in execpath:
        full_path = os.path.join(os.path.expanduser(path), exec_name)
        if os.path.exists(full_path):
            return full_path
        for suffix in suffixes:
            if os.path.exists(full_path + suffix):  # pragma: no cover
                return full_path + suffix
    return None  # Couldn't find anything.

def resolve_exec(cmd, rel_to=None):
    """Disambiguate spaces in a string which may or may not be shell-quoted"""
    split_cmd = shlex.split(cmd)

    if rel_to:
        cmd = os.path.join(rel_to, cmd)
        split_cmd[0] = os.path.join(rel_to, split_cmd[0])

    return split_cmd if (which(split_cmd[0]) and not which(cmd)) else [cmd]

def script_precheck(path):
    """Basic checks which should be run before inspecting any script."""
    return os.path.isfile(path) and os.stat(path).st_size <= MAX_SCRIPT_SIZE

@total_ordering
class GameEntry(object):
    """
    @todo: Decide on a proper definition of equality.
    """
    def __init__(self, name, icon=None, provider=None, *args, **kwargs):
        self.name = name
        self.icon = icon
        self.provider = provider

        if args or kwargs:
            log.debug("Unconsumed arguments: %r, %r", args, kwargs)

    def __eq__(self, other):
        return self.name == other.name

    def __gt__(self, other):
        return self.name > other.name

    def __str__(self):
        return self.name
    __repr__ = __str__

    def is_installed(self):
        return False

@total_ordering
class InstalledGameEntry(GameEntry):
    """
    @todo: Mechanism for sub-entries like "Config" as in Desura.
    """
    def __init__(self, name, argv, icon=None, tryexec=None, use_terminal=False,
                 *args, **kwargs):
        super(InstalledGameEntry, self).__init__(name, icon, *args, **kwargs)

        self.argv = argv
        self.tryexec = tryexec or argv[0]
        self.use_terminal = use_terminal

    def __eq__(self, other):
        return (self.name, self.argv) == (other.name, other.argv)

    def __repr__(self):
        return "%s (%s)" % (self.name, self.argv)

    def is_installed(self):
        return bool(which(self.tryexec) and which(self.argv[0]))
