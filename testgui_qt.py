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

from PyQt5.QtCore import QAbstractTableModel, QSortFilterProxyModel, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QHeaderView,
                             QListView, QStackedWidget)
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

class GameListModel(QAbstractTableModel):
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

    def rowCount(self, parent):
        if parent and parent.isValid():
            # Not tree-structured
            return 0
        return len(self.games)

    def columnCount(self, parent):
        if parent and parent.isValid():
            return 0
        return 2

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
                icon = QIcon.fromTheme(icon_name)

            # Resort to PyXDG to walk the fallback chain properly
            # TODO: Better resolution handling
            if not icon or icon.isNull():
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

    # TODO: Rewrite to subclass QAbstractTableModel instead
    def headerData(self, section, orientation, role):
        # TODO: Can Qt provide automatic hide/show-able column support?
        if role == Qt.DisplayRole:
            if section == 0:
                return "Title"
            elif section == 1:
                return "Provider"

    def data(self, index, role):
        if (not index.isValid()) or index.row() >= len(self.games):
            return None

        # TODO: Make the game resolution order deterministic between the two
        #       copies of Race The Sun that I have installed.
        #       (Python 2.x with GTK+ finds 1.42 first and Python 3.x with Qt
        #        finds 1.10 first and the two versions have different icons
        #        so that's how I noticed.)
        row = index.row()
        col = index.column()

        if col == 0:
            if role == Qt.DisplayRole:
                return self.games[row].name
            elif role == Qt.DecorationRole:
                return self.get_icon(self.games[row].icon)
            elif role == Qt.ToolTipRole:
                return self.games[row].summarize()
        elif col == 1 and role == Qt.DisplayRole:
            return ', '.join(self.games[row].provider)

def unbotch_icons(root, mappings):
    """Fix 'pyuic seems to not load Qt Designer-specified theme icons'

    Basically, a helper to manually amend the config in the code.
    """

    for wid_tuple in mappings:
        icon = QIcon.fromTheme(mappings[wid_tuple])

        # Support fallback to more than one filename
        # TODO: Decide on a way to use the Qt fallback mechanism
        #       and support multiple icon resolutions.
        #       (Possibly amending the theme search path somehow?)
        if icon.isNull():
            path_base = os.path.join(os.path.dirname(__file__),
                                     'gui_qt', mappings[wid_tuple])
            for ext in ('svgz', 'svg' 'png'):
                icon_path = '{}.{}'.format(path_base, ext)
                if os.path.exists(icon_path):
                    icon = QIcon(os.path.join(icon_path))
                    if not icon.isNull():
                        break

        widget = root.findChild(wid_tuple[0], wid_tuple[1]).setIcon(icon)

# Help prevent crashes on exit
# Source: http://pyqt.sourceforge.net/Docs/PyQt5/gotchas.html
app = None

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
        (QAction, 'actionShow_categories_pane'): 'view-split-left-right',
        (QAction, 'actionRescan'): 'reload',
    })
    view_buttons = {
        (QAction, 'actionIcon_View'): 'view-list-icons-symbolic',
        (QAction, 'actionList_View'): 'view-list-compact-symbolic',
        (QAction, 'actionDetailed_List_View'): 'view-list-details-symbolic'
    }
    unbotch_icons(window, view_buttons)
    makeActionGroup(window, [x[1] for x in view_buttons.keys()])

    # Hook up the signals
    # TODO: Un-bodge this
    stackedwidget = window.stack_view_games
    listview = window.view_games
    tableview = window.view_games_detailed
    def set_listview_mode(mode, checked):
        if checked:
            stackedwidget.setCurrentIndex(0)
            listview.setViewMode(mode)

    def set_tableview_mode(checked):
        if checked:
            stackedwidget.setCurrentIndex(1)

    for action, viewmode in (
                (window.actionIcon_View, QListView.IconMode),
                (window.actionList_View, QListView.ListMode),
                                  ):
        action.triggered.connect(lambda checked, viewmode=viewmode:
                                 set_listview_mode(viewmode, checked))
    window.actionDetailed_List_View.triggered.connect(set_tableview_mode)

    # Needed so the first click on the header with the default sort order
    # doesn't behave like a no-op.
    tableview.sortByColumn(0, Qt.AscendingOrder)

    # Qt Designer has a bug which resets this in the file (without resetting
    # the checkbox in the property editor) whenever I switch focus away in the
    # parent QStackedWidget, so I have to force it here.
    tableview.horizontalHeader().setVisible(True)

    # It's *FAR* too easy to switch this to the wrong value in Qt Designer.
    # TODO: Set up robusy sync between this and the button group
    stackedwidget.setCurrentIndex(0)

    model = GameListModel(get_games())
    sorted_model = model.as_sorted()
    window.view_games.setModel(sorted_model)
    window.view_games_detailed.setModel(sorted_model)

    # Synchronize selection behaviour between the two views
    window.view_games.setSelectionModel(
        window.view_games_detailed.selectionModel())

    # Prevent the columns from bunching up in the detail view
    # http://www.qtcentre.org/threads/3417-QTableWidget-stretch-a-column-other-than-the-last-one?p=18624#post18624
    header = tableview.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.Interactive)
    tableview.resizeColumnsToContents()
    header.setSectionResizeMode(0, QHeaderView.Stretch)
    # TODO: Figure out how to set a reasonable default AND remember the user's
    #       preferred dimensions for interactive columns.

    window.show()

    # Prevent crash-on-exit behaviour
    # Source: http://stackoverflow.com/a/12457209/435253
    retval = app.exec_()
    app.deleteLater()
    sys.exit(retval)

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
