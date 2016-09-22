"""Main window subclass to encapsulate workarounds for Qt Designer flaws

Based on this stack overflow QA pair:
    http://stackoverflow.com/a/21267698/435253
"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QMainWindow

from .helpers import (bind_all_standard_keys, make_action_group,
                      unbotch_icons)

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Bind standard hotkeys for closing the window
        bind_all_standard_keys(QKeySequence.Close, self.close, self)

        # TODO: Load saved geometry

    def configure_children(self):
        """Call this to finish initializing after child widgets are added

        TODO: Figure out how to automate the process of running this after
              actions that would be done in setupUi when translating the .ui
              file dynamically where there's no setupUi to wrap.
        """

        # Work around Qt Designer shortcomings
        unbotch_icons(self, {
            (QAction, 'actionShow_categories_pane'): 'view-split-left-right',
            (QAction, 'actionRescan'): 'reload',
        })
        view_buttons = {
            (QAction, 'actionIcon_View'): 'view-list-icons-symbolic',
            (QAction, 'actionList_View'): 'view-list-compact-symbolic',
            (QAction, 'actionDetailed_List_View'): 'view-list-details-symbolic'
        }
        unbotch_icons(self, view_buttons)
        self.view_actions = make_action_group(self,
            [x[1] for x in view_buttons.keys()])

        # TODO: More automatic way for this
        self.stack_view_games.configure_children()
        self.loadState()

    def loadState(self):
        # Restore saved settings
        # (Cannot be called from __init__ because children aren't there yet)
        settings = QSettings()
        settings.beginGroup("mainwindow")
        for role in ('geometry', 'state'):
            data = settings.value(role)
            if data:
                getattr(self, 'restore' + role.title())(data)
        settings.endGroup()

        # Match dock toggle button to dock state
        # TODO: Fix this so it doesn't cause hide the pane by default
        #self.actionShow_categories_pane.setChecked(
        #    self.dock_categories.isVisible())

        # Match view selector buttons to stacked widget state
        # TODO: Fix this so it doesn't cause an unpredictable one to start
        # checked
        #currentIdx = self.stack_view_games.currentIndex()
        #self.view_actions.actions()[currentIdx].setChecked(True)

    def closeEvent(self, event):
        """Save settings on exit"""
        # TODO: Display an "are you sure" dialog if not in trayable mode
        settings = QSettings()
        settings.beginGroup("mainwindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        settings.endGroup()

        # Can't be called by stack_view_games.destroyed() for GC reasons
        self.stack_view_games.saveState()

        super(MainWindow, self).closeEvent(event)
