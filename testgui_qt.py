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
ICON_SIZE = 64

import logging, os, sys
log = logging.getLogger(__name__)

from PyQt5.QtCore import QAbstractListModel, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QListView
from PyQt5.uic import loadUi

from xdg.IconTheme import getIconPath

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
        self.icon_cache = {}  # TODO: Do this properly

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

    # TODO: Do this properly
    def get_icon(self, icon_name):
        """Workaround for Qt not implementing a fallback chain in fromTheme"""
        # Always let the cache service requests first
        if icon_name in self.icon_cache:
            return self.icon_cache[icon_name]

        # Skip right to the fallback if it's None or an empty string
        if icon_name:
            # Give Qt the opportunity to make a fool out of itself
            if os.path.isfile(icon_name):
                icon = QIcon(icon_name)
            else:
                icon = QIcon.fromTheme(icon_name,
                                       QIcon.fromTheme(FALLBACK_ICON))

            # Resort to PyXDG to walk the fallback chain properly
            # TODO: Better resolution handling
            icon = QIcon(getIconPath(icon_name, ICON_SIZE,
                                     theme=QIcon.themeName()))
        else:
            icon = None

        # If we still couldn't get a result, retrieve the fallback icon in a
        # way which will allow a cache entry here without duplication
        if not icon or icon.isNull() and icon_name != FALLBACK_ICON:
            icon = self.get_icon(FALLBACK_ICON)

        # Populate the cache
        self.icon_cache[icon_name] = icon
        return icon

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
            return self.get_icon(self.games[index].icon)
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
