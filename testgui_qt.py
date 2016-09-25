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
from PyQt5.QtWidgets import QShortcut

from src.interfaces import PLUGIN_TYPES
from yapsy.PluginManager import PluginManagerSingleton

from src.game_providers import get_games

from gui_qt.application import Application
from gui_qt.model import GameListModel

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

    app = Application(sys.argv)

    # Bind a placeholder to Ctrl+3 so it won't result in a spurious 3 being
    # typed into the search box if a user hits it by accident.
    QShortcut(QKeySequence(Qt.CTRL + Qt.Key_3), app.mainwin).activated.connect(
        lambda: log.error("Thumbnail view not yet implemented"))

    # Temporary binding point between model and app until I refactor the model
    model = get_model().as_sorted()
    app.set_model(model)

    def rescan():
        model.setSourceModel(get_model())
        app.mainwin.searchBar.clear()
    app.mainwin.actionRescan.triggered.connect(rescan)

    # Ensure F5 continues to work if the toolbar is hidden
    app.mainwin.addAction(app.mainwin.actionRescan)

    app.mainwin.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
