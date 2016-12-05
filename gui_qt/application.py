"""QApplication subclass to make it easier to browse code based on roles"""

import os

# pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication
from PyQt5.uic import loadUi

from PyQt5_fixes.helpers import bind_all_standard_keys
from .model import CategoriesModel

UI_FILE_PATH = os.path.join(os.path.dirname(__file__), os.pardir, 'testgui.ui')

class Application(QApplication):
    mainwin = None
    model = None

    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)

        # Globally set values used by QSettings (rather than repeatedly)
        self.setOrganizationName("ssokolow.com")
        self.setOrganizationDomain("ssokolow.com")
        self.setApplicationName("LazyGLaunch")

        # Load the various widgets from the UI files
        # (Must come after setting the org and app names for QSettings)
        with open(UI_FILE_PATH) as fobj:
            self.mainwin = loadUi(fobj)

        # TODO: More automatic way for this
        self.mainwin.configure_children()
        self.gamesview = self.mainwin.stack_view_games

        # Hook the search box up to the model filter
        self.mainwin.searchBar.regexpChanged.connect(self.searchChanged)

        # Hook up the quit hotkey
        bind_all_standard_keys(QKeySequence.Quit, self.quit, self.mainwin,
                               Qt.ApplicationShortcut)

    def set_model(self, model):
        self.model = model

        # Hook up the signals
        self.gamesview.setModel(model)

        # Hook up the categories panel
        # TODO: Refactor this so I don't need to recreate the cat_model proxy
        #       every time I hook in a new source model
        cat_model = CategoriesModel(model)
        self.mainwin.view_categories.setModel(cat_model)

    @pyqtSlot('QRegExp')
    def searchChanged(self, regexp):
        self.model.setFilterRegExp(regexp)
        self.gamesview.ensureSelection()
        self.gamesview.ensureVisible()

    def exec_(self):
        """Wrapper for QApplication.exec_ which fixes crash-on-exit behaviour

        Source: http://stackoverflow.com/a/12457209/435253
        """
        retval = super(Application, self).exec_()
        self.deleteLater()
        return retval
