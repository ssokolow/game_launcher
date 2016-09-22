#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Game Launcher with no dependencies on external services
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Qt Test GUI for game launcher experiment"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import logging, os, sys
log = logging.getLogger(__name__)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QApplication, QShortcut
from PyQt5.uic import loadUi

from src.interfaces import PLUGIN_TYPES
from yapsy.PluginManager import PluginManagerSingleton

from src.game_providers import get_games

from gui_qt.model import CategoriesModel, GameListModel
from gui_qt.helpers import make_action_group, unbotch_icons

# Help prevent crashes on exit
# Source: http://pyqt.sourceforge.net/Docs/PyQt5/gotchas.html
app = None

def get_model():
    """Placeholder for 'Rescan' until I'm ready to do it properly"""
    # TODO: Do this in the background with some kind of progress indicator
    return GameListModel(get_games())

def main():
    """The main entry point, compatible with setuptools entry points."""

    # TODO: Unify this into a single file all frontends can import
    plugin_mgr = PluginManagerSingleton.get()
    plugin_mgr.setPluginPlaces(['plugins'])  # TODO: Explicit __file__-rel.
    plugin_mgr.setCategoriesFilter({x.plugin_type: x for x in PLUGIN_TYPES})
    plugin_mgr.collectPlugins()

    print('Plugins Found:\n\t{}'.format('\n\t'.join(str(x.plugin_object)
        for x in sorted(plugin_mgr.getAllPlugins(),
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
    make_action_group(window, [x[1] for x in view_buttons.keys()])

    model = get_model().as_sorted()

    # Hook up the signals
    stackedwidget = window.stack_view_games
    stackedwidget.configure_children()  # TODO: More automatic way to do this?
    stackedwidget.setModel(model)

    # Hook up the categories panel
    cat_model = CategoriesModel(model)
    window.view_categories.setModel(cat_model)

    # Hook the search box up to the model filter
    # (We connect ensureSelection and ensureVisible here rather than in Qt
    #  Designer to make all three slots run in the right order)
    window.searchBar.regexpChanged.connect(model.setFilterRegExp)
    window.searchBar.regexpChanged.connect(stackedwidget.ensureSelection)
    window.searchBar.regexpChanged.connect(stackedwidget.ensureVisible)

    def rescan():
        model.setSourceModel(get_model())
        window.searchBar.clear()
    window.actionRescan.triggered.connect(rescan)

    # Bind a placeholder to Ctrl+3 so it won't result in a spurious 3 being
    # typed into the search box if a user hits it by accident.
    QShortcut(QKeySequence(Qt.CTRL + Qt.Key_3), window).activated.connect(
        lambda: log.error("Thumbnail view not yet implemented"))

    window.show()

    # Prevent crash-on-exit behaviour
    # Source: http://stackoverflow.com/a/12457209/435253
    retval = app.exec_()
    app.deleteLater()
    sys.exit(retval)

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
