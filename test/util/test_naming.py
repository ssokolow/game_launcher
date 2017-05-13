"""Tests for util.naming"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from os.path import join, dirname
from ..common import json_aggregate_harness, load_json_map

# TODO: Decide on a name for the program and rename "src"
from src.util.naming import filename_to_name, titlecase_up, PROGRAM_EXTS

# Minimal set of extensions one might expect a game to use
# (For whitelist-based extension stripping so it's not too greedy)
test_program_exts = (
    '.air', '.swf', '.jar',
    '.sh', '.py', '.pl',
    '.exe', '.bat', '.cmd', '.pif',
    '.bin',
    '.desktop',
    '.nes',
    '.love'
)

def test_filename_to_name():
    """Test for sufficient accuracy of guesses by filename_to_name()"""
    test_data_path = join(dirname(__file__), 'filename_to_name_data.json')
    return json_aggregate_harness(load_json_map(test_data_path),
                                  filename_to_name)

def test_titlecase_up_integration():
    """Test that titlecase_up() is callable from Python"""
    assert titlecase_up("hello") == "Hello"

def test_program_ext_completeness():
    """Test for comprehensiveness of PROGRAM_EXTS-stripping test"""
    missed = [x for x in test_program_exts if x not in PROGRAM_EXTS]
    assert not missed, "Extensions not in PROGRAM_EXTS: %s" % missed

    excess = [x for x in PROGRAM_EXTS if x not in test_program_exts]
    assert not excess, "Extensions in PROGRAM_EXTS but not test: %s" % excess
