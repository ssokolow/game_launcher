"""Tests for util.naming"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import json
from os.path import join, dirname

# TODO: Decide on a name for the program and rename "src"
from src.util.naming import filename_to_name, PROGRAM_EXTS

# TODO: unittest.TestCase for titlecase_up()

# Minimal set of extensions one might expect a game to use
# (For whitelist-based extension stripping so it's not too greedy)
test_program_exts = (
    '.air', '.swf', '.jar',
    '.sh', '.py', '.pl',
    '.exe', '.bat', '.cmd', '.pif',
    '.bin',
    '.desktop',
)

test_data_path = join(dirname(__file__), 'filename_to_name_data.json')
with open(test_data_path) as fobj:
    filename_test_map = json.load(fobj)
    filename_test_map.update({'test' + x: {'ideal': 'Test'}
                              for x in test_program_exts})

for key, val in filename_test_map.items():
    if 'ideal' not in val:
        raise ValueError("Missing ideal value for %s in " %
                         key, test_data_path)
    try:
        if val.get('MUST_AUDIT'):
            raise ValueError("%s contains MUST_AUDIT values" % test_data_path)
    except AttributeError:
        raise ValueError("Value for %s is not a dict" % key)

def test_program_ext_completeness():
    """Test for comprehensiveness of PROGRAM_EXTS-stripping test"""
    missed = [x for x in test_program_exts if x not in PROGRAM_EXTS]
    assert not missed, "Extensions not in PROGRAM_EXTS: %s" % missed

    excess = [x for x in PROGRAM_EXTS if x not in test_program_exts]
    assert not excess, "Extensions in PROGRAM_EXTS but not test: %s" % excess

def test_filename_to_name():
    """Test for sufficient accuracy of guesses by filename_to_name()"""
    score = 0
    failures = {}

    for key, params in filename_test_map.items():
        valid_results = [params['ideal']] + params.get('acceptable', [])
        result = filename_to_name(key)

        if result in valid_results:
            this_score = -valid_results.index(result)
        else:
            this_score = -10

        score += this_score
        if this_score < 0:
            failures[key] = (key, result, valid_results[0])

    fail_count, total_count = len(failures), len(filename_test_map)
    message = "\nFailed to perfectly guess %s of %s titles (%.2f%%):\n" % (
                fail_count, total_count, (fail_count / total_count * 100))
    for val in failures.values():
        message += "\t%-35s-> %-35s (not %s)\n" % val
    message += "Final accuracy score: %s" % score
    print(message)

    assert score > -10
