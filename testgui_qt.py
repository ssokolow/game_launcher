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
from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QListView
from PyQt5.uic import loadUi

from src.interfaces import PLUGIN_TYPES
from yapsy.PluginManager import PluginManagerSingleton

from src.game_providers import get_games

def makeActionGroup(parent, action_names):
    """Helper for cleanly grouping actions by name"""
    group = QActionGroup(parent)
    for action_name in action_names:
        group.addAction(parent.findChild(QAction, action_name))

class GameListModel(QAbstractListModel):
    def __init__(self, data_list):
        self.games = data_list
        super(GameListModel, self).__init__()

    def as_sorted(self):
        model_sorted = QSortFilterProxyModel()
        model_sorted.setDynamicSortFilter(True)
        model_sorted.setSortCaseSensitivity(Qt.CaseInsensitive)
        model_sorted.setSourceModel(self)
        model_sorted.sort(0, Qt.AscendingOrder)
        return model_sorted

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

def unbotch_icons(root, mappings):
    """Fix 'pyuic seems to not load Qt Designer-specified theme icons'

    Basically, a helper to manually amend the config in the code.
    """

    for wid_tuple in mappings:
        icon = QIcon.fromTheme(mappings[wid_tuple])
        widget = root.findChild(wid_tuple[0], wid_tuple[1]).setIcon(icon)

def main():
    """The main entry point, compatible with setuptools entry points."""

    pluginManager = PluginManagerSingleton.get()
    pluginManager.setPluginPlaces(['plugins'])  # TODO: Explicit __file__-rel.
    pluginManager.setCategoriesFilter({x.plugin_type: x for x in PLUGIN_TYPES})
    pluginManager.collectPlugins()

    print('Plugins Found:\n\t{}'.format('\n\t'.join(str(x.plugin_object)
        for x in sorted(pluginManager.getAllPlugins(),
               key=lambda x: x.plugin_object.precedence))))

    app = QApplication(sys.argv)

    with open(os.path.join(os.path.dirname(__file__), 'testgui.ui')) as fobj:
        window = loadUi(fobj)

    model = GameListModel(get_games())
    model_sorted = QSortFilterProxyModel()
    model_sorted.setDynamicSortFilter(True)
    model_sorted.setSortCaseSensitivity(Qt.CaseInsensitive)
    model_sorted.setSourceModel(model)
    model_sorted.sort(0, Qt.AscendingOrder)

    # Work around Qt Designer shortcomings
    unbotch_icons(window, {
        (QAction, 'actionIcon_View'): 'view-list-icons-symbolic',
        (QAction, 'actionList_View'): 'view-list-details-symbolic'
    })
    makeActionGroup(window, ['actionIcon_View', 'actionList_View'])

    # Hook up the signals
    # TODO: Un-bodge this
    listview = window.findChild(QListView, 'view_games')
    def set_listview_mode(mode, checked):
        if checked:
            listview.setViewMode(mode)

    for action_name, viewmode in (
                ('actionIcon_View', QListView.IconMode),
                ('actionList_View', QListView.ListMode),
            ):
        window.findChild(QAction, action_name).triggered.connect(
            lambda checked, viewmode=viewmode: set_listview_mode(
                viewmode, checked))

    model = GameListModel(get_games())
    window.view_games.setModel(model.as_sorted())
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
