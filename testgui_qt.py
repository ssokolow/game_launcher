#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[application description here]"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Qt Test GUI for game launcher experiment"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import logging, os, sys
log = logging.getLogger(__name__)

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QListView)
from PyQt5.uic import loadUi

from src.interfaces import PLUGIN_TYPES
from yapsy.PluginManager import PluginManagerSingleton

from src.game_providers import get_games

from gui_qt.model import GameListModel

def makeActionGroup(parent, action_names):
    """Helper for cleanly grouping actions by name"""
    group = QActionGroup(parent)
    for action_name in action_names:
        group.addAction(parent.findChild(QAction, action_name))

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

        root.findChild(wid_tuple[0], wid_tuple[1]).setIcon(icon)

# Help prevent crashes on exit
# Source: http://pyqt.sourceforge.net/Docs/PyQt5/gotchas.html
app = None

def get_model():
    """Placeholder for 'Rescan' until I'm ready to do it properly"""
    # TODO: Do this in the background with some kind of progress indicator
    return GameListModel(get_games())

def main():
    """The main entry point, compatible with setuptools entry points."""

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
    makeActionGroup(window, [x[1] for x in view_buttons.keys()])

    model = get_model().as_sorted()

    # Hook up the signals
    stackedwidget = window.stack_view_games
    stackedwidget.configure_children()  # TODO: More automatic way to do this?
    stackedwidget.setModel(model)

    # Hook the filter box up to the model filter
    # (We connect ensureSelection and ensureVisible here rather than in Qt
    #  Designer to make all three slots run in the right order)
    window.searchBar.textChanged.connect(model.setFilterFixedString)
    window.searchBar.textChanged.connect(stackedwidget.ensureSelection)
    window.searchBar.textChanged.connect(stackedwidget.ensureVisible)

    # Call again through a QTimer because, otherwise, it doesn't work with very
    # short filters. (I think Qt is doing deferred layout to remain responsive
    # and that's throwing off scrollTo() with large result sets)
    # FIXME: Do this properly (maybe a verticalScrollBar().rangeChanged()
    #        wrapper in stackedwidget and then connect it to ensureVisible?)
    window.searchBar.textChanged.connect(lambda:
        QTimer.singleShot(100, stackedwidget.ensureVisible))

    def rescan():
        model.setSourceModel(get_model())
        window.searchBar.clear()
    window.actionRescan.triggered.connect(rescan)

    window.show()

    # Prevent crash-on-exit behaviour
    # Source: http://stackoverflow.com/a/12457209/435253
    retval = app.exec_()
    app.deleteLater()
    sys.exit(retval)

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
