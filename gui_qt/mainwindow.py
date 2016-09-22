"""Main window subclass to encapsulate workarounds for Qt Designer flaws

Based on this stack overflow QA pair:
    http://stackoverflow.com/a/21267698/435253
"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

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
        make_action_group(self, [x[1] for x in view_buttons.keys()])
