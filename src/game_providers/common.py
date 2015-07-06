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

import errno, logging, os, subprocess
from functools import total_ordering

from ..util.common import which
from ..util.executables import Roles
# TODO: Verify I've moved all relevant uses of Roles into .util.executables

# TODO: Include my patched xdg-terminal or some other fallback mechanism
# TODO: Move this and most other constants to a config.py for visibility
TERMINAL_CMD = ['xterm', '-e']

log = logging.getLogger(__name__)

# --- Entry Classes ---

@total_ordering
class GameEntry(object):
    """
    @todo: Decide on a proper definition of equality.
    """

    base_path = None

    # pylint: disable=too-many-arguments
    def __init__(self, name, icon=None, provider=None, description=None,
                 commands=None, *args, **kwargs):
        self.name = name
        self.icon = icon
        self._provider = provider or []
        self._description = description
        self.commands = commands or []

        if isinstance(self._provider, basestring):
            self._provider = [self._provider]
        if not isinstance(self._provider, set):
            self._provider = set(self._provider)

        if args or kwargs:
            log.debug("Unconsumed arguments: %r, %r", args, kwargs)

    def __eq__(self, other):
        return self.name.lower() == other.name.lower()

    def __gt__(self, other):
        return self.name > other.name

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        """@todo: Make this read out the subentries too"""
        return "<%s (%s)>" % (self.name, ', '.join(self.provider))

    @property
    def description(self):
        """Make a best effort to return a description for this entry."""
        return self._description or ([x.description
                                      for x in self.commands
                                      if x.description] + [None])[0]

    def first_launcher(self, role=None, fallback_unknown=False):
        """Get the first usable launcher matching the specified role."""
        result = [x for x in self.commands
                  if (not role or x.role == role) and x.is_executable()]
        if not result and fallback_unknown:
            return self.first_launcher(Roles.unknown)
        return (result + [None])[0]

    def is_executable(self, role=None):
        """Returns true if is_executable() == True for any contained launchers.

        @param role: If specified, constrains the search.
        @type role: L{GameLauncher.Roles}
        """
        return any(x.is_executable() for x in self.commands
                   if not role or x.role == role)

    # TODO: Rename to providers?
    @property
    def provider(self):
        """Deduce the provider list from the commands"""
        return self._provider.union(x.provider for x in self.commands
                                    if x.provider)

    def summarize(self):
        """Return all human-relevant metadata in formatted plaintext form

        @todo: Fix Don't Starve's description
        """
        lines = ["%s (%s)" % (self.name, ', '.join(self.provider))]
        if self.description and self.description != self.name:
            lines.extend(('', self.description))
        if any(x for x in self.categories if x != 'Game'):
            lines.extend(('', 'Categories:'))
            lines.extend(['- ' + x.strip() for x in self.categories if
                          x.strip() not in ('', 'Game')])
        return '\n'.join(lines)

    def update(self, other):
        """Merge in metadata from another entry object."""
        for name in ('icon', 'provider', '_description'):
            if hasattr(other, name) and not hasattr(self, name):
                setattr(self, name, getattr(other, name))

        self.provider.update(other.provider)

    # TODO: Rename to categories and allow non-launcher content like providers?
    @property
    def categories(self):
        """Deduce the provider list from the commands"""
        return [cat for cats in self.commands for cat in cats]

@total_ordering
class InstalledGameEntry(GameEntry):
    """
    @todo: Add a metadata field for the containing folder (eg. WINEPREFIX) so
           it can be used for disk space usage calculation, post-uninstall
           deletion, and bounding icon searches.
    @todo: Some kind of mechanism for registering things like Wine prefixes,
           install directories, and the like as deduplication keys.
    """

    def __init__(self, base_path, **kwargs):
        super(InstalledGameEntry, self).__init__(**kwargs)

        # TODO: Apply COMMON_DIRS filtering here so it's unified
        # XXX: What if multiple copies are installed? Allow a list?
        if base_path:
            self.base_path = os.path.normcase(os.path.abspath(base_path))

    def __eq__(self, other):
        """@todo: Make this more discerning"""
        if (self.base_path and other.base_path and
            self.base_path == other.base_path):
            return True

        argv_match = False
        for x in self.commands:
            for y in other.commands:
                argv_match = argv_match or x.argv == y.argv
        return super(InstalledGameEntry, self).__eq__(other) or argv_match

    @property
    def categories(self):
        """Make a best effort to return a description for this entry.

        @todo: Decide whether I should filter for Roles.play and then merge."""
        return self._description or ([x.categories
                                      for x in self.commands
                                      if x.categories] + [[]])[0]


# --- Subentry Classes ---

@total_ordering
class GameSubentry(object):
    """Base class defining the interface for a game subentry."""
    # pylint: disable=too-few-public-methods

    # pylint: disable=too-many-arguments
    def __init__(self, name, provider, role=None, icon=None, sort_key=None,
                 **kwargs):
        """
        @param name: Human-readable label for this subentry
        @param provider: The game provider which generated this subentry.
        @type role: L{Roles}
        @type icon: C{str}
        @type sort_key: C{tuple(str)}
        """
        self.name = name
        self.icon = icon
        self.provider = provider
        self.role = role or Roles.guess(self.name)

        # Python 3 doesn't allow comparing disparate types so we choose the
        # convention that sort_key will be a tuple of strings
        self.sort_key = sort_key or tuple(name)

        if not isinstance(self.role, Roles):
            raise TypeError("role must be of type GameSubentry.Roles, not %s"
                            % type(self.role))

        if kwargs:
            log.debug("Unconsumed arguments: %r", kwargs)

    def _cmp(self, other):
        """ORDER BY self.role, self.sort_key for @total_ordering"""
        return (cmp(self.role, other.role) or
                cmp(self.sort_key, other.sort_key))

    # TODO: Define __gt__ more cleanly
    # TODO: redefine __eq__ to be suitable for deduplication.
    #       (And decide how to handle picking the more fields)

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __gt__(self, other):
        return self._cmp(other) > 0

    def __repr__(self):
        return "<%s from %s>" % (self.name, self.provider)

    def is_executable(self):  # pylint: disable=no-self-use
        """Override to define a "can we launch this?" check"""
        return False

class GameLauncher(GameSubentry):
    """Represents an executable command within a game entry.

    @note: Use of positional arguments is not supported.
    """

    # pylint: disable=too-many-arguments,too-many-instance-attributes
    def __init__(self, argv, path=None, tryexec=None, description=None,
                 use_terminal=False, categories=None, keywords=None,
                 **kwargs):
        """
        @param argv: The command to run to launch this.
        @param path: The working directory from which to run this.
        @param tryexec: An extra path for L{is_executable} to depend on.
        @param description: A game synopsis for display to the user.
        @param use_terminal: Set to C{True} if the game requires a terminal
            window but argv does not hard-code one.
        @param categories: Applicable XDG Desktop Entry specification
            category keywords.
            (See http://standards.freedesktop.org/menu-spec/1.0/apa.html )
        @param keywords: Additional keywords to aid searching in launchers.
        @param kwargs: See L{GameSubentry}

        @type argv: C{str}
        @type path: C{str}
        @type tryexec: C{bool}
        @type description: C{str}
        @type use_terminal: C{bool}
        @type categories: C{list(str)}
        """
        super(GameLauncher, self).__init__(**kwargs)

        self.argv = argv
        self.path = path
        self.tryexec = tryexec
        self.description = description
        self.use_terminal = use_terminal
        self.categories = categories or []
        self.keywords = keywords  # TODO: What format?

        # Give entries with identical names a more stable ordering
        self.sort_key = (self.name, self.argv)

        assert isinstance(self.argv, list), self.argv
        # Minimize load when comparing by argv by caching normalization
        self.argv[0] = os.path.normcase(os.path.normpath(self.argv[0]))

    def __eq__(self, other):
        # Redefine equality more strictly in terms of argv
        return hasattr(other, 'argv') and self.argv == other.argv

    def __repr__(self):
        # Amend the repr() representation with argv
        return "<%s from %s (%s)>" % (self.name, self.provider, self.argv)

    def is_executable(self):
        """Defined in terms of C{tryexec} and C{argv[0]}"""
        if self.tryexec and not which(self.tryexec):
            return False
        return bool(which(self.argv[0]))

    def run(self):
        """Launch this entry as a subprocess using the contained metadata"""
        # Work around things like Desura expecting Windows-style PWD behaviour
        if not self.path:
            self.path = os.path.dirname(which(self.argv[0]))
            if not os.path.exists(self.path):
                log.error("Failed to generate valid $PWD (%s)", self.path)
                self.path = None

        argv = self.argv
        if self.use_terminal:
            argv = TERMINAL_CMD + argv

        log.info("Spawning %r with cwd=%r", self.argv, self.path)
        try:
            return subprocess.Popen(self.argv, cwd=self.path).pid
            # TODO: Rework so I can capture output and display it on unclean
            #       exit (eg. error while loading shared libraries: ...)
        except OSError, err:
            if err.errno != errno.ENOEXEC:
                raise
            if not self.argv[0].endswith('.sh'):
                raise
            with file(self.argv[0]) as fobj:
                if fobj.read(2) == '#!':
                    raise
            # If we reach here, it's a shellscript with no shebang
            return subprocess.Popen(['/bin/sh'] + self.argv, cwd=self.path).pid
