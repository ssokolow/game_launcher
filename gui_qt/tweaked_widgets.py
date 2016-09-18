"""Widget subclasses used in conjunction with Qt Designer's widget promotion
to keep the code's structure clean.
"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QSize, Qt, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QHeaderView, QListView,
                             QStackedWidget, QTableView, QTreeView)

from .helpers import bind_all_standard_keys


class BugFixListView(QListView):
    """A subclass of QListView which fixes various papecut issues.

    - Scroll by pixel (or by a reasonable approximation of traditional clicky
      scroll-wheel steps) rather than by lines, which fails with large icons.
    """

    def updateGeometries(self):
        """Fix Qt 5.2.1's broken decision to map the OS "1 step = X lines"
        scrolling setting without accounting for very tall lines.

        (Here, "1 step = 3 lines" makes `singleStep` so close to `pageStep`
        that I don't see a difference.)

        Replace it with the "1 QWheelEvent unit = 1px" decision that has
        served GTK+ 2.x well and appears to be what `QTableView` winds up
        with thanks to capping icons at roughly the same height as the text.

        Source: http://stackoverflow.com/a/2036242 and trial-and-error tuning
        """
        super(BugFixListView, self).updateGeometries()
        self.verticalScrollBar().setSingleStep(15)

class BugFixTableView(QTableView):
    """A subclass of QTableView which fixes various papercut issues.

    - Counter Qt Designer bug which forces horizontal header visibility off
    - Ensure the header sort indicator actually works properly on first click
    - Implement stretch for the first column rather than the last
    - Set up QListView-like Home/End behaviour
    """

    def __init__(self, *args, **kwargs):
        super(BugFixTableView, self).__init__(*args, **kwargs)


        # Fix the behaviour of the Home and End keys
        bind_all_standard_keys(QKeySequence.MoveToStartOfLine,
                               self.selectFirst, self,
                               Qt.WidgetWithChildrenShortcut)
        bind_all_standard_keys(QKeySequence.MoveToEndOfLine,
                               self.selectLast, self,
                               Qt.WidgetWithChildrenShortcut)

    def setModel(self, model):
        """Set the model view, with fixes for papercut bugs"""
        super(BugFixTableView, self).setModel(model)

        # Qt Designer has a bug which resets this in the file (without
        # resetting the checkbox in the property editor) whenever I switch
        # focus away in the parent QStackedWidget, so I have to force it here.
        # TODO: Figure out how to run this after actions that would be done in
        #       setupUi when translating the .ui file dynamically where there's
        #       no setupUi to wrap.
        self.horizontalHeader().setVisible(True)

        # Explicitly set the view's sorting state to work around a bug where
        # the first click on the header has no effect.
        if hasattr(model, 'sortColumn') and hasattr(model, 'sortOrder'):
            self.sortByColumn(model.sortColumn(), model.sortOrder())

        # Prevent the columns from bunching up in the detail view
        # http://www.qtcentre.org/threads/3417-QTableWidget-stretch-a-column-other-than-the-last-one?p=18624#post18624
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.resizeColumnsToContents()
        # TODO: Figure out how to set a reasonable default AND remember the
        #       user's preferred dimensions for interactive columns.

    @pyqtSlot()
    def selectFirst(self):
        """Reset selection to the first item

        (Used to implement Home key fix)"""
        self.setCurrentIndex(self.model().index(0, 0))

    @pyqtSlot()
    def selectLast(self):
        """Reset selection to the last item

        (Used to implement End key fix)"""
        self.setCurrentIndex(self.model().index(
                self.model().rowCount() - 1, 0))

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
        self.ensureSelection()
        next_row = self.tableview.currentIndex().row() + 1
        if next_row < self.model.rowCount():
            self.tableview.setCurrentIndex(self.model.index(next_row, 0))

    @pyqtSlot()
    def selectPrevious(self):
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

class NarrowerTreeView(QTreeView):  # pylint: disable=no-init,R0903
    """A subclass of QTreeView which works around Qt Designer's inability to
    set default sizes for QDockWidget.

    Source:
        http://stackoverflow.com/a/13715893
    """
    def sizeHint(self):  # pylint: disable=no-self-use
        """Set a more reasonable starting width for the parent dock widget."""
        return QSize(150, 75)
