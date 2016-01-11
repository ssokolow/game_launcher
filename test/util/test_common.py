"""Tests for util.common"""
from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from os.path import join, dirname
from ..common import json_aggregate_harness, load_json_map

# TODO: Decide on a name for the program and rename "src"
from src.util.common import humansort_key

# TODO: Decide what to do with this function since it's used to BUILD tests
#       and is never used at runtime
import random
def generate_tst_pair(values, key_func=lambda x: x, pre_transform=lambda x: x):
    """Generate a sorting test pair from a list of strings.

    (Used to ease the construction of the constant strings used for sanity
     checks against the default bytewise sorting behaviour.)

     eg. generate_tst_pair(string.lowercase, lambda x: x.lower(),
                           lambda x: x.upper() if ord(x) % 2 else x)
     """
    values = [pre_transform(x) for x in values]

    before = list(values)
    random.shuffle(before)
    before = tuple(before)

    if key_func:
        after = tuple(sorted(values, key=key_func))
    else:
        after = tuple(values)
    return (before, after)

humansort_key_map = (
    # Basic sanity checks
    (('3', '4', '6', '7', '1', '0', '9', '8', '5', '2'),
     ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')),
    (('V', 'I', 'P', 'X', 'S', 'N', 'C', 'R', 'Q', 'D', 'J', 'M', 'H', 'O',
      'G', 'L', 'W', 'T', 'U', 'K', 'B', 'Z', 'Y', 'E', 'F', 'A'),
     ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
      'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z')),
    (('p', 'o', 'f', 'x', 's', 'r', 'g', 'm', 'u', 'l', 'i', 'b', 'c', 'w',
      'n', 'd', 'v', 'a', 'j', 'h', 'y', 'z', 'k', 't', 'e', 'q'),
     ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
      'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z')),
    # Combinatorial sanity checks
    (('caa', 'cba', 'aab', 'aac', 'aaa', 'aba', 'cbc', 'abc', 'abb'),
     ('aaa', 'aab', 'aac', 'aba', 'abb', 'abc', 'caa', 'cba', 'cbc')),
    # Base case-insensitivity
    (('x', 'r', 'l', 'f', 'C', 'M', 'U', 'd', 'G', 'I', 'Y', 'O', 'j', 'Q',
      'p', 'h', 't', 'b', 'W', 'K', 'E', 'z', 'n', 'S', 'v', 'A'),
     ('A', 'b', 'C', 'd', 'E', 'f', 'G', 'h', 'I', 'j', 'K', 'l', 'M', 'n',
      'O', 'p', 'Q', 'r', 'S', 't', 'U', 'v', 'W', 'x', 'Y', 'z')),
    # TODO: Combinatorial case-insensitivity
    # Intuitive number ordering
    (('32', '30', '1', '11', '0', '12', '31', '2', '10'),
     ('0', '1', '2', '10', '11', '12', '30', '31', '32')),
    # TODO: Intuitive number ordering within larger strings

    # TODO: Before implementing any further, switch to the natsort library
    #       so further tests can be written to test its suitability before
    #       I potentially reinvent the wheel.
    # TODO: Ignore punctuation

    # XXX: Stuff that GTK+ file managers can't do below this point
    #     (Separate functions for titles and filename sorting to be intuitive?)
    # TODO: Sort roman numerals 1-19 equivalently to numbers
    #     (A compromise based on observation of Japanese game titles)
    # TODO: Sort "Foo" and "Foo: The Bar" before "Foo 2: The Bazzing"
    #     (Will require a robust test corpus prior to implementation)
    # TODO: Ignore "The" prefixes (And within titles?)
    # TODO: Unicode
    #   http://python3porting.com/problems.html#sorting-unicode
    #   http://stackoverflow.com/q/1097908

    # XXX: Do I want to support non-string values?
)

def check_humansort_key(before, after):
    result = tuple(sorted(before, key=humansort_key))
    # TODO: Look into a better way to render this.
    assert result == after, ("humansort_key(%r)\n\t= %r\n\t(not %r)" %
                              (before, result, after))

def test_humansort_key():
    """Test for intuitive results from humansort_key()"""
    for before, after in humansort_key_map:
        yield check_humansort_key, before, after
