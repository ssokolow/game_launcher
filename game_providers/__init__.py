import logging
from itertools import chain

from . import xdg_menu, desura, playonlinux, fallback

log = logging.getLogger(__name__)

# TODO: Move priority ordering control into backend metadata
PROVIDERS = [xdg_menu, desura, playonlinux, fallback]

def get_games():
    result_sets, results = {}, []

    # Get raw results
    for entry in sorted(chain(*[x.get_games() for x in PROVIDERS])):
        if not entry.is_executable():
            log.info("Skipping entry %s from %s. Not executable:\n\t%s",
                     entry,
                     entry.provider,
                     '\n\t'.join(' '.join(x.argv) for x in entry.commands))
            continue

        result_sets.setdefault(entry.name, []).append(entry)

    # Merge and deduplicate
    for resultset in result_sets.values():
        first = resultset.pop(0)
        results.append(first)

        for entry in resultset[:]:
            if first == entry:
                first.update(entry)
                resultset.remove(entry)
            else:
                results.append(entry)

    # TODO: Dedupe
    return results

