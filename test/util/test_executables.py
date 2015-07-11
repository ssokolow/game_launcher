"""Tests for util.executables"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from os.path import join, dirname
from ..common import json_aggregate_harness, load_json_map

# TODO: Decide on a name for the program and rename "src"
from src.util.executables import Roles

# TODO: unittest.TestCase for classify_executable()

test_data_path = join(dirname(__file__), 'Roles_guess_data.json')

def test_Roles_guess():
    """Test for sufficient accuracy of guesses by Roles.guess()"""
    return json_aggregate_harness(load_json_map(test_data_path), Roles.guess,
                                  lambda x: getattr(Roles, x, Ellipsis))
