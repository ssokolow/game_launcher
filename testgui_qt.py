#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[application description here]"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Qt Test GUI for game launcher experiment"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

# TODO: Support per-backend fallback icons (eg. GOG and PlayOnLinux)
FALLBACK_ICON = "applications-games"


import logging, os, sys
log = logging.getLogger(__name__)

from PyQt5.QtCore import QAbstractListModel, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication
from PyQt5.uic import loadUi

from src.game_providers import get_games

class GameListModel(QAbstractListModel):
    def __init__(self, data_list):
        self.games = data_list
        super(GameListModel, self).__init__()

    def rowCount(self, _):
        return len(self.games)

    def data(self, index, role):
        if (not index.isValid()) or index.row() >= len(self.games):
            return None

        # TODO: Make the game resolution order deterministic between the two
        #       copies of Race The Sun that I have installed.
        #       (Python 2.x with GTK+ finds 1.42 first and Python 3.x with Qt
        #        finds 1.10 first and the two versions have different icons
        #        so that's how I noticed.)
        index = index.row()
        if role == Qt.DisplayRole:
            return self.games[index].name
        elif role == Qt.DecorationRole:
            icon_name = self.games[index].icon
            if not icon_name:
                return None
            elif os.path.isfile(icon_name):
                return QIcon(icon_name)
            else:
                return QIcon.fromTheme(icon_name,
                                       QIcon.fromTheme(FALLBACK_ICON))
        elif role == Qt.ToolTipRole:
            return self.games[index].summarize()

def main():
    """The main entry point, compatible with setuptools entry points."""
    app = QApplication(sys.argv)

    with open(os.path.join(os.path.dirname(__file__), 'testgui.ui')) as fobj:
        window = loadUi(fobj)

    model = GameListModel(get_games())
    model_sorted = QSortFilterProxyModel()
    model_sorted.setDynamicSortFilter(True)
    model_sorted.setSortCaseSensitivity(Qt.CaseInsensitive)
    model_sorted.setSourceModel(model)
    model_sorted.sort(0, Qt.AscendingOrder)

    window.view_games.setModel(model_sorted)
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
