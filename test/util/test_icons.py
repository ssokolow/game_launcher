"""Tests for util.icons"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import json
from os.path import join, dirname
from ..common import json_aggregate_harness, load_json_map

# TODO: Decide on a name for the program and rename "src"
from src.util.icons import pick_icon

def test_pick_icon():
    """Test that pick_icon() picks a good enough icon enough of the time"""
    test_data_path = join(dirname(__file__), 'pick_icon_data.json')
    return json_aggregate_harness(load_json_map(test_data_path),
                                  lambda x: pick_icon(*x),
                                  resolve_key_cb=json.loads)
