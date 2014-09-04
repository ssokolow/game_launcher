#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An advanced GUI for organizing and launching games on Linux, regardless of
how they were installed.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Unified Game Launcher"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import sys
from PyQt5 import QtWidgets

# -- Code Here --

def main():
    """The main entry point, compatible with setuptools entry points."""
    app = QtWidgets.QApplication(sys.argv)

    w = QtWidgets.QWidget()
    w.resize(350, 150)
    w.move(300, 300)
    w.setWindowTitle(__appname__)
    w.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
