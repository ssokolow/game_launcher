from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

from functools import total_ordering

# TODO: Include my patched xdg-terminal or some other fallback mechanism
TERMINAL_CMD = 'xterm -e %s'

@total_ordering
class GameEntry(object):
    """
    @todo: Decide on a proper definition of equality.
    """
    def __init__(self, name, icon, *args, **kwargs):
        self.name = name
        self.icon = icon

        # Shut up PyLint without silencing real "unused argument" warnings
        args, kwargs  # pylint: disable=pointless-statement

    def __eq__(self, other):
        return self.name == other.name

    def __gt__(self, other):
        return self.name > other.name

    def __str__(self):
        return self.name
    __repr__ = __str__

@total_ordering
class InstalledGameEntry(GameEntry):
    """
    @todo: Mechanism for sub-entries like "Config" as in Desura.
    """
    def __init__(self, name, icon, argv, tryexec=None, *args, **kwargs):
        super(InstalledGameEntry, self).__init__(name, icon, *args, **kwargs)

        self.argv = argv
        self.tryexec = tryexec or argv[0]

    def __eq__(self, other):
        return (self.name, self.argv) == (other.name, other.argv)

    def __repr__(self):
        return "%s (%s)" % (self.name, self.argv)

