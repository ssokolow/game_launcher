"""Tests for util.executables"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import json
from os.path import join, dirname

# TODO: Decide on a name for the program and rename "src"
from src.util.executables import Roles

# TODO: unittest.TestCase for classify_executable()

test_data_path = join(dirname(__file__), 'Roles_guess_data.json')
with open(test_data_path) as fobj:
    filename_test_map = json.load(fobj)

# TODO: Deduplicate this with the test_naming.py copy
for key, val in filename_test_map.items():
    if 'ideal' not in val:
        raise ValueError("Missing ideal value for %s in " %
                         key, test_data_path)
    try:
        if val.get('MUST_AUDIT'):
            raise ValueError("%s contains MUST_AUDIT values" % test_data_path)
    except AttributeError:
        raise ValueError("Value for %s is not a dict" % key)

def test_Roles_guess():
    """Test for sufficient accuracy of guesses by Roles.guess()"""
    score = 0
    failures = {}

    for key, params in filename_test_map.items():
        # Ellipsis used as a value which cannot occur in Roles.guess's output
        best = params.get('attainable') or params.get('ideal')
        valid_results = [best] + params.get('acceptable', [])
        valid_results = [(getattr(Roles, x, Ellipsis) if x is not None else x)
                         for x in valid_results]

        best = getattr(Roles, best, Ellipsis) if best is not None else best
        ideal = (getattr(Roles, params.get('ideal'), Ellipsis)
                 if isinstance(best, basestring) else best)

        result = Roles.guess(key)

        if result != best and result == ideal:
            print("Exceeded Expectations with \"%s\"" % key)
            this_score = 2
        elif result in valid_results:
            this_score = -valid_results.index(result)
        else:
            this_score = -10

        score += this_score
        if this_score < 0:
            failures[key] = (key, result, valid_results[0])

    fail_count, total_count = len(failures), len(filename_test_map)
    message = "\nFailed to attainably guess %s of %s roles (%.2f%%):\n" % (
                fail_count, total_count, (fail_count / total_count * 100))
    for val in failures.values():
        message += "\t%-60s-> %-40s (not %s)\n" % val
    message += "Final accuracy score: %s" % score
    print(message)

    assert score > -10
