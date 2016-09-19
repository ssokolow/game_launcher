"""Implementation of promoted stacked widget for Qt Designer"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QListView, QStackedWidget, QTableView

class GamesView(QStackedWidget):
    """Encapsulation for the stuff that ties together stack_view_games and its
    children in testgui.ui"""

    model = None
    listview = None
    tableview = None
    selectionmodel = None

    def configure_children(self):
        """Call this to finish initializing after child widgets are added

        (Basically looking up references to the children and then applying a
         bag of fixes for Qt Designer bugs)

        TODO: Figure out how to automate the process of running this after
              actions that would be done in setupUi when translating the .ui
              file dynamically where there's no setupUi to wrap.
        """
        # It's *FAR* too easy to switch this to the wrong value in Qt Designer.
        # TODO: Set up robust sync between this and the button group
        self.setCurrentIndex(0)

        # Cache simple references to the views
        self.listview = self.findChild(QListView, 'view_games')
        self.tableview = self.findChild(QTableView, 'view_games_detailed')

        #self.listview.setItemDelegate(AugmentedListDelegate(self))

        # Hook up double-click/enter handlers
        self.listview.activated.connect(self.launchEntry)
        self.tableview.activated.connect(self.launchEntry)

    def currentView(self):
        """Retrieve a reference to the currently visible view"""
        idx = self.currentIndex()
        if idx == 0:
            return self.listview
        elif idx == 1:
            return self.tableview

    def setModel(self, model):
        """Set the model on both views within the compound object.

        (Also ensures the table view's header will properly reflect the sort
        order and sets the views up to share a common selection model.)
        """
        # Actually hook up the model
        self.model = model
        self.listview.setModel(model)
        self.tableview.setModel(model)

        # Synchronize selection behaviour between the two views
        self.selectionmodel = self.tableview.selectionModel()
        self.listview.setSelectionModel(self.selectionmodel)

    @pyqtSlot()
    def ensureSelection(self):
        """Select the first item if nothing is currently selected"""
        if not self.selectionmodel.hasSelection():
            self.selectFirst()

    @pyqtSlot()
    def ensureVisible(self):
        """Scroll to ensure that the selected item is visible in the viewport
        of the currently selected view."""
        if self.selectionmodel and self.selectionmodel.hasSelection():
            # Rely on the default "EnsureVisible" hint for scrollTo()
            self.currentView().scrollTo(self.selectionmodel.currentIndex())

    @pyqtSlot()
    def focus(self):
        """Focus the currently visible inner widget"""
        self.currentView().setFocus(Qt.OtherFocusReason)
        self.ensureSelection()

    @pyqtSlot()
    @pyqtSlot('QModelIndex')
    def launchEntry(self, index=None):
        """Handler to launch games on double-click"""
        index = index or self.selectionmodel.currentIndex()
        if not (index and index.isValid()):
            return

        # TODO: Make this not a stop-gap solution
        cmd = self.model.data(index, Qt.UserRole).default_launcher
        if cmd:
            cmd.run()

    @pyqtSlot()
    def selectNext(self):
        """Move the selection the next row in the model"""
        self.ensureSelection()
        next_row = self.tableview.currentIndex().row() + 1
        if next_row < self.model.rowCount():
            self.tableview.setCurrentIndex(self.model.index(next_row, 0))

    @pyqtSlot()
    def selectPrevious(self):
        """Move the selection the previous row in the model"""
        self.ensureSelection()
        prev_row = self.tableview.currentIndex().row() - 1
        if prev_row >= 0:
            self.tableview.setCurrentIndex(self.model.index(prev_row, 0))

    @pyqtSlot()
    @pyqtSlot(bool)
    def setIconViewMode(self, checked=True):
        """Slot which can be directly bound by QAction::toggled(bool)"""
        if checked:
            self.setCurrentIndex(0)
            self.listview.setViewMode(QListView.IconMode)
            self.ensureVisible()

    @pyqtSlot()
    @pyqtSlot(bool)
    def setListViewMode(self, checked=True):
        """Slot which can be directly bound by QAction::toggled(bool)"""
        if checked:
            self.setCurrentIndex(0)
            self.listview.setViewMode(QListView.ListMode)
            self.ensureVisible()

    @pyqtSlot()
    @pyqtSlot(bool)
    def setTableViewMode(self, checked=True):
        """Slot which can be directly bound by QAction::toggled(bool)"""
        if checked:
            self.setCurrentIndex(1)
            self.ensureVisible()

    @pyqtSlot()
    def selectFirst(self):
        """Reset selection to the first item"""
        self.tableview.selectFirst()

    @pyqtSlot()
    def selectLast(self):
        """Reset selection to the first item"""
        self.tableview.selectLast()
