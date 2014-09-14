from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

from functools import total_ordering

@total_ordering
class GameEntry(object):
    """
    @todo: Decide on a proper definition of equality.
    @todo: Mechanism for sub-entries like "Config" as in Desura.
    """
    def __init__(self, name, icon, argv, tryexec=None):
        self.name = name
        self.icon = icon
        self.argv = argv
        self.tryexec = tryexec or argv[0]

    def __eq__(self, other):
        return (self.name, self.argv) == (other.name, other.argv)

    def __gt__(self, other):
        return self.name > other.name

    def __repr__(self):
        return "%s (%s)" % (self.name, self.argv)

    def __str__(self):
        return self.name
