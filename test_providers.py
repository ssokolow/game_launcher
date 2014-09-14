from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

from itertools import chain
from game_providers import xdg_menu, desura, playonlinux

games = sorted(chain(*(x.get_games() for x in (xdg_menu, desura, playonlinux))))
# TODO: Dedupe
print('\n'.join(repr(x) for x in games))
print("%d games found" % len(games))
