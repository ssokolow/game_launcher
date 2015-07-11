"""Tests for util.naming"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from os.path import join, dirname
from ..common import json_aggregate_harness, load_json_map

# TODO: Decide on a name for the program and rename "src"
from src.util.naming import filename_to_name, titlecase_up, PROGRAM_EXTS

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

titlecase_up_map = {
    '1234567890': '1234567890',
    'testtesttest': 'Testtesttest',
    'foo_bar_baz_quux': 'Foo_Bar_Baz_Quux',
    'foo-bar-baz-quux': 'Foo-Bar-Baz-Quux',
    'green eggs and spam': 'Green Eggs And Spam',
    'hello': 'Hello',
    'ScummVM': 'ScummVM',
    'bit.trip.runner': 'Bit.Trip.Runner',
    'FTL': 'FTL',
}

def test_titlecase_up():
    """Test for correct function of titlecase_up()"""
    # TODO: Make this much more thorough
    for before, after in titlecase_up_map.items():
        result1 = titlecase_up(before)
        assert result1 == after, "%s != %s" % (result1, after)

        result2 = titlecase_up(result1)
        assert result2 == result1, "%s != %s" % (result2, result1)

def test_program_ext_completeness():
    """Test for comprehensiveness of PROGRAM_EXTS-stripping test"""
    missed = [x for x in test_program_exts if x not in PROGRAM_EXTS]
    assert not missed, "Extensions not in PROGRAM_EXTS: %s" % missed

    excess = [x for x in PROGRAM_EXTS if x not in test_program_exts]
    assert not excess, "Extensions in PROGRAM_EXTS but not test: %s" % excess

def test_filename_to_name():
    """Test for sufficient accuracy of guesses by filename_to_name()"""
    test_data_path = join(dirname(__file__), 'filename_to_name_data.json')
    return json_aggregate_harness(load_json_map(test_data_path),
                                  filename_to_name)
