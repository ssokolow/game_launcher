"""Framework for extracting a list of games from the system"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import logging
from itertools import chain

# TODO: Decide on a name for the program and rename "src"
from src import interfaces

log = logging.getLogger(__name__)

# TODO: Audit all backends to ensure that they meet minimum acceptable
#       standards for explaining what inputs they ignored and why when
#       at debug-level logging (in case of false negatives).

# TODO: This only performs acceptably with a warm cache. Rework it as a
#       generator so we can display a visual progress indication.
def get_games():
    """Use all available backends to retrieve a deduplicated list of games"""
    results_raw, results = [], []

    providers = interfaces.IGameProvider.get_all()

    # Get raw results
    for entry in sorted(chain(*[x.get_games() for x in providers])):
        if not entry.is_executable():
            log.info("Skipping entry %s from %s. Not executable:\n\t%s",
                     entry,
                     entry.provider,
                     '\n\t'.join(' '.join(x.argv) for x in entry.commands))
            continue

        # Look into having entries generate a tuple for use as a dict key
        # for sorting into buckets prior to comparison
        results_raw.append(entry)

    # TODO: Probably a good idea to note which results weren't re-discovered
    #       by the fallback walker and manually run them through it to see
    #       if anything turns up.

    # Merge and deduplicate
    # TODO: Redesign to not be O(n^2)
    while results_raw:
        val1 = results_raw.pop(0)
        results.append(val1)

        for val2 in results_raw[:]:
            if val1 == val2:
                results_raw.remove(val2)
                val1.update(val2)
                break

    return results
