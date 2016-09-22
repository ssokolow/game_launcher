"""Main window subclass to encapsulate workarounds for Qt Designer flaws

Based on this stack overflow QA pair:
    http://stackoverflow.com/a/21267698/435253
"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QMainWindow

from .helpers import (bind_all_standard_keys, make_action_group,
                      set_action_icon, unbotch_icons)

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Bind standard hotkeys for closing the window
        bind_all_standard_keys(QKeySequence.Close, self.close, self)

    def configure_children(self):
        """Call this to finish initializing after child widgets are added

        TODO: Figure out how to automate the process of running this after
              actions that would be done in setupUi when translating the .ui
              file dynamically where there's no setupUi to wrap.
        """

        # Work around Qt Designer shortcomings
        unbotch_icons(self, {(QAction, 'actionRescan'): 'reload'})
        view_buttons = {
            (QAction, 'actionIcon_View'): 'view-list-icons-symbolic',
            (QAction, 'actionList_View'): 'view-list-compact-symbolic',
            (QAction, 'actionDetailed_List_View'): 'view-list-details-symbolic'
        }
        unbotch_icons(self, view_buttons)
        self.view_actions = make_action_group(self,
            [x[1] for x in view_buttons.keys()])

        self._add_toolbar_buttons()

        # TODO: More automatic way for this
        self.stack_view_games.configure_children()
        self.loadWindowState()

    def _add_toolbar_buttons(self):
        # Hook up the toggle button for the categories pane
        cat_action = self.dock_categories.toggleViewAction()
        cat_action.setToolTip("Show categories pane (F9)")
        cat_action.setShortcut(QKeySequence(Qt.Key_F9))
        set_action_icon(cat_action, 'view-split-left-right')
        self.toolBar.addAction(cat_action)

        # Make the shortcut work even when the toolbar is hidden
        self.addAction(cat_action)

    def closeEvent(self, event):
        """Save settings on exit"""
        # TODO: Display an "are you sure" dialog if not in trayable mode
        self.saveWindowState()
        super(MainWindow, self).closeEvent(event)

    def loadWindowState(self):
        # Restore saved settings
        # (Cannot be called from __init__ because children aren't there yet)
        settings = QSettings()
        settings.beginGroup("mainwindow")
        for role in ('geometry', 'state'):
            data = settings.value(role)
            if data:
                getattr(self, 'restore' + role.title())(data)

        # Match view selector buttons to stacked widget state
        current_mode = settings.value('view_mode')
        for action in self.view_actions.actions():
            if action.objectName() == current_mode:
                action.setChecked(True)
                break

        settings.endGroup()

    def saveWindowState(self):
        settings = QSettings()
        settings.beginGroup("mainwindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

        for action in self.view_actions.actions():
            if action.isChecked():
                settings.setValue("view_mode", action.objectName())
                break
        settings.endGroup()
