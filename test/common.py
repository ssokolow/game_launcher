"""Common code for tests which convert a JSON test set into a numeric score"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "MIT"

import json, sys
if sys.version_info.major > 2:
    # pylint: disable=redefined-builtin,invalid-name
    basestring = str  # pragma: nocover

def load_json_map(json_path):
    """Load a validate a JSON definition of a set of subtests."""
    with open(json_path) as fobj:
        test_map = json.load(fobj)

    for key, val in test_map.items():
        if 'ideal' not in val:         # pragma: nocover
            raise ValueError("Missing ideal value for %s in " %
                             key, json_path)
        try:
            if val.get('MUST_AUDIT'):  # pragma: nocover
                raise ValueError("%s contains MUST_AUDIT values" %
                                 json_path)
        except AttributeError:         # pragma: nocover
            raise ValueError("Value for %s is not a dict" % key)

    return test_map

def json_aggregate_harness(test_map, test_cb,
                           resolve_result_cb=lambda x: x,
                           resolve_key_cb=lambda x: x):
    """
    @param resolve_result_cb: Callback for resolving custom datatypes from JSON
    @param resolve_key_cb: Callback for deserializing keys not directly
        supported by JSON or Python dicts.
    """
    score = 0
    failures = []

    for key, params in test_map.items():
        key = resolve_key_cb(key)
        best = params.get('attainable') or params.get('ideal')
        valid_results = [best] + params.get('acceptable', [])

        # Ellipsis used as a value which cannot occur in Roles.guess's output
        valid_results = [(resolve_result_cb(x) if x is not None else x)
                         for x in valid_results]

        best = resolve_result_cb(best) if best is not None else best
        ideal = (resolve_result_cb(params.get('ideal'))
                 if isinstance(best, basestring) else best)

        result = test_cb(key)

        if result != best and result == ideal:  # pragma: nocover
            print("Exceeded Expectations with \"%s\"" % key)
            this_score = 2
        elif result in valid_results:
            this_score = -valid_results.index(result)
        else:
            this_score = -10

        score += this_score
        if this_score < 0:
            failures.append((key, result, valid_results[0]))

    fail_count, total_count = len(failures), len(test_map)
    message = "\nFailed to attainably guess %s of %s values (%.2f%%):\n" % (
                fail_count, total_count, (fail_count / total_count * 100))
    for val in failures:
        val = list(val)
        val[0] = str(val[0])[:60]
        val = tuple(val)
        message += "\t%-60s-> %-40s (not %s)\n" % val
    message += "Final accuracy score: %s" % score
    print(message)

    assert score > -10
