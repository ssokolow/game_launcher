"""
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

import enum, logging, os, shlex, subprocess
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

def script_precheck(path):
    """Basic checks which should be run before inspecting any script."""
    return os.path.isfile(path) and os.stat(path).st_size <= MAX_SCRIPT_SIZE

@total_ordering
class GameEntry(object):
    """
    @todo: Decide on a proper definition of equality.
    """
    def __init__(self, name, icon=None, provider=None, description=None,
                 *args, **kwargs):
        self.name = name
        self.icon = icon
        self.provider = provider
        self._description = description

        if args or kwargs:
            log.debug("Unconsumed arguments: %r, %r", args, kwargs)

    def __eq__(self, other):
        return self.name == other.name

    def __gt__(self, other):
        return self.name > other.name

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return repr(self.name)

    @property
    def description(self):
        """Override this to implement custom description resolution"""
        return self._description

    # pylint: disable=no-self-use,unused-argument
    def is_executable(self, role=None):
        """Override in subclasses defining installed games"""
        return False

@total_ordering
class InstalledGameEntry(GameEntry):
    """
    @todo: Add a metadata field for the containing folder (eg. WINEPREFIX) so
           it can be used for disk space usage calculation and post-uninstall
           deletion.
    @todo: Some kind of mechanism for registering things like Wine prefixes,
           install directories, and the like as deduplication keys.
    """
    def __init__(self, name, icon=None, commands=None, *args, **kwargs):
        super(InstalledGameEntry, self).__init__(name, icon, *args, **kwargs)

        self.commands = commands or []

    def __eq__(self, other):
        """@todo: Make this more discerning"""
        return self.name == other.name

    def __repr__(self):
        """@todo: Make this read out the subentries too"""
        return "<%s (%s)>" % (self.name, self.provider)

    def first_launcher(self, role=None):
        return ([x for x in self.commands if not role or x.role == role] +
                [None])[0]

    @property
    def description(self):
        """Make a best effort to return a description for this entry."""
        return self._description or ([x.description
                                      for x in self.commands
                                      if x.description] + [None])[0]

    @property
    def xdg_categories(self):
        """Make a best effort to return a description for this entry.

        @todo: Decide whether I should filter for Roles.play and then merge."""
        return self._description or ([x.xdg_categories
                                      for x in self.commands
                                      if x.xdg_categories] + [[]])[0]


    def is_executable(self, role=None):
        """Returns true if is_executable() == True for any contained launchers.

        @param role: If specified, constrains the search.
        @type role: L{GameLauncher.Roles}
        """
        return any(x.is_executable() for x in self.commands
                   if not role or x.role == role)


class GameLauncher(object):
    """Represents an executable command within a game entry.
    @todo: Mechanism for sub-entries like "Config" as in Desura.
    """

    @enum.unique
    class Roles(enum.Enum):
        """An enumeration of the roles L{GameLauncher} instances can take.

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
                for result, matches in {
                    cls.play: ('play', 'start', 'client'),
                    cls.configure: ('config', 'setup', 'settings'),
                    cls.install: ('install',),
                    cls.uninstall: ('uninst', 'remove'),
                }.items():
                    for fragment in matches:
                        if fragment in name:
                            return result
            return cls.unknown

    # pylint: disable=too-many-arguments
    def __init__(self, argv, provider, role=None, name=None, path=None,
                 icon=None, tryexec=None, use_terminal=False,
                 description=None, xdg_categories=None, *args, **kwargs):

        self.argv = argv
        self.path = path
        self.provider = provider
        self.role = role or self.Roles.guess(name) or self.Roles.guess(argv[0])
        self.tryexec = tryexec or argv[0]

        self.name = name
        self.icon = icon
        self.use_terminal = use_terminal
        self.description = description
        self.xdg_categories = xdg_categories or []

        if args or kwargs:
            log.debug("Unconsumed arguments: %r, %r", args, kwargs)

    def __eq__(self, other):
        return self.argv == other.argv

    def __repr__(self):
        return "<%s from %s (%s)>" % (self.name, self.provider, self.argv)

    def is_executable(self):
        """Returns True if C{tryexec} and C{argv[0]} are executable."""
        if self.tryexec and not which(self.tryexec):
            return False

        return bool(which(self.argv[0]))

    def run(self):
        # Work around things like Desura expecting Windows-style PWD behaviour
        if not self.path:
            self.path = os.path.dirname(which(self.argv[0]))
            if not os.path.exists(self.path):
                log.error("Failed to generate valid $PWD (%s)", self.path)
                self.path = None

        print("Spawning %s" % self.argv)
        return subprocess.Popen(self.argv, cwd=self.path).pid
