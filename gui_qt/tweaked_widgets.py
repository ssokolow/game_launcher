"""Widget subclasses used in conjunction with Qt Designer's widget promotion
to keep the code's structure clean.
"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtWidgets import (QHeaderView, QLineEdit, QListView, QTableView,
                             QToolBar, QSizePolicy, QStackedWidget, QTreeView,
                             QWidget)

class GamesView(QStackedWidget):
    """Encapsulation for the stuff that ties together stack_view_games and its
    children in testgui.ui"""

    listview = None
    tableview = None

    def __init__(self, *args, **kwargs):
        super(GamesView, self).__init__(*args, **kwargs)

    def configure_children(self):
        """Call this to finish initializing after child widgets are added

        (Basically looking up references to the children and then applying a
         bag of fixes for Qt Designer bugs)
        """
        self.listview = self.findChild(QListView, 'view_games')
        self.tableview = self.findChild(QTableView, 'view_games_detailed')

        # Qt Designer has a bug which resets this in the file (without
        # resetting the checkbox in the property editor) whenever I switch
        # focus away in the parent QStackedWidget, so I have to force it here.
        self.tableview.horizontalHeader().setVisible(True)

        # It's *FAR* too easy to switch this to the wrong value in Qt Designer.
        # TODO: Set up robust sync between this and the button group
        self.setCurrentIndex(0)

    def setModel(self, model):
        """Set the model on both views within the compound object.

        (Also ensures the table view's header will properly reflect the sort
        order and sets the views up to share a common selection model.)
        """
        # Explicitly set the view's sorting state to work around a bug where
        # the first click on the header has no effect.
        if hasattr(model, 'sortColumn') and hasattr(model, 'sortOrder'):
            self.tableview.sortByColumn(model.sortColumn(), model.sortOrder())

        # Actually hook up the model
        self.listview.setModel(model)
        self.tableview.setModel(model)

        # Synchronize selection behaviour between the two views
        self.listview.setSelectionModel(
            self.tableview.selectionModel())

        # Prevent the columns from bunching up in the detail view
        # http://www.qtcentre.org/threads/3417-QTableWidget-stretch-a-column-other-than-the-last-one?p=18624#post18624
        header = self.tableview.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableview.resizeColumnsToContents()
        # TODO: Figure out how to set a reasonable default AND remember the
        #       user's preferred dimensions for interactive columns.

    @pyqtSlot()
    def focus(self):
        """Focus the correct inner widget"""
        idx = self.currentIndex()
        if idx == 0:
            self.listview.setFocus(Qt.OtherFocusReason)
        elif idx == 1:
            self.tableview.setFocus(Qt.OtherFocusReason)

    @pyqtSlot()
    @pyqtSlot(bool)
    def setIconViewMode(self, checked=True):
        """Slot which can be directly bound by QAction::toggled(bool)"""
        if checked:
            self.setCurrentIndex(0)
            self.listview.setViewMode(QListView.IconMode)

    @pyqtSlot()
    @pyqtSlot(bool)
    def setListViewMode(self, checked=True):
        """Slot which can be directly bound by QAction::toggled(bool)"""
        if checked:
            self.setCurrentIndex(0)
            self.listview.setViewMode(QListView.ListMode)

    @pyqtSlot()
    @pyqtSlot(bool)
    def setTableViewMode(self, checked=True):
        """Slot which can be directly bound by QAction::toggled(bool)"""
        if checked:
            self.setCurrentIndex(1)

class NarrowerTreeView(QTreeView):  # pylint: disable=no-init,R0903
    """A subclass of QTreeView which works around Qt Designer's inability to
    set default sizes for QDockWidget.

    Source:
        http://stackoverflow.com/a/13715893
    """
    def sizeHint(self):  # pylint: disable=no-self-use
        """Set a more reasonable starting width for the parent dock widget."""
        return QSize(150, 75)

class SearchToolbar(QToolBar):  # pylint: disable=too-few-public-methods
    """Search toolbar with a few tweaks not possible in pure Qt Designer

    Sources:
     - http://www.setnode.com/blog/right-aligning-a-button-in-a-qtoolbar/
    """
    DESIRED_WIDTH = 150

    returnPressed = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(SearchToolbar, self).__init__(*args, **kwargs)

        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)

        hotkey = QKeySequence(QKeySequence.Find)

        self.filter_box = QLineEdit(self)
        self.filter_box.setPlaceholderText("Search... ({})".format(
            hotkey.toString()))
        self.filter_box.setClearButtonEnabled(True)
        self.filter_box.setMaximumSize(self.DESIRED_WIDTH,
            self.filter_box.maximumSize().height())
        self.addWidget(self.filter_box)

        shortcut = QShortcut(hotkey, self)
        shortcut.activated.connect(lambda:
            self.filter_box.setFocus(Qt.ShortcutFocusReason))

        # Proxy the returnPressed signal up to where Qt Designer can handle it
        self.filter_box.returnPressed.connect(self.returnPressed.emit)
        # TODO: Implement the clear() slot and textChanged(QString) signal