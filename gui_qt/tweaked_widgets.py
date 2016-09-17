from PyQt5.QtCore import QSize, Qt, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtWidgets import (QHeaderView, QLineEdit, QListView, QTableView,
                             QToolBar, QSizePolicy, QStackedWidget, QTreeView,
                             QWidget)

class GamesView(QStackedWidget):
    """Encapsulation for the stuff that ties together stack_view_games and its
    children in testgui.ui"""
    def __init__(self, *args, **kwargs):
        super(GamesView, self).__init__(*args, **kwargs)

    def configure_children(self):
        """Call this to finish initializing after child widgets are added

        (Basically looking up references to the children and then applying a
         bag of fixes for Qt Designer bugs)
        """
        self.listview = self.findChild(QListView, 'view_games')
        self.tableview = self.findChild(QTableView, 'view_games_detailed')

        # Needed so the first click on the header with the default sort order
        # doesn't behave like a no-op.
        # TODO: Figure out how to do this just prior to hooking up the model
        # and how to read the sort order from the proxy model, if present.
        self.tableview.sortByColumn(0, Qt.AscendingOrder)

        # Qt Designer has a bug which resets this in the file (without
        # resetting the checkbox in the property editor) whenever I switch
        # focus away in the parent QStackedWidget, so I have to force it here.
        self.tableview.horizontalHeader().setVisible(True)

        # It's *FAR* too easy to switch this to the wrong value in Qt Designer.
        # TODO: Set up robust sync between this and the button group
        self.setCurrentIndex(0)

    def setModel(self, model):
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
        self.tableview.resizeColumnsToContents()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # TODO: Figure out how to set a reasonable default AND remember the
        #       user's preferred dimensions for interactive columns.

    @pyqtSlot()
    @pyqtSlot(bool)
    def setIconViewMode(self, checked=True):
        if checked:
            self.setCurrentIndex(0)
            self.listview.setViewMode(QListView.IconMode)

    @pyqtSlot()
    @pyqtSlot(bool)
    def setListViewMode(self, checked=True):
        if checked:
            self.setCurrentIndex(0)
            self.listview.setViewMode(QListView.ListMode)

    @pyqtSlot()
    @pyqtSlot(bool)
    def setTableViewMode(self, checked=True):
        if checked:
            self.setCurrentIndex(1)

class NarrowerTreeView(QTreeView):
    """A subclass of QTreeView which works around Qt Designer's inability to
    set default sizes for QDockWidget.

    Source:
        http://stackoverflow.com/a/13715893
    """
    def sizeHint(self):
        return QSize(150, 75)

class SearchToolbar(QToolBar):  # pylint: disable=too-few-public-methods
    """Search toolbar with a few tweaks not possible in pure Qt Designer

    Sources:
     - http://www.setnode.com/blog/right-aligning-a-button-in-a-qtoolbar/
    """
    DESIRED_WIDTH = 150

    def __init__(self, *args, **kwargs):
        super(SearchToolbar, self).__init__(*args, **kwargs)

        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)

        self.filter_box = QLineEdit(self)
        self.filter_box.setPlaceholderText("Search...")
        self.filter_box.setClearButtonEnabled(True)
        self.filter_box.setMaximumSize(self.DESIRED_WIDTH,
            self.filter_box.maximumSize().height())
        self.addWidget(self.filter_box)

        shortcut = QShortcut(QKeySequence.Find, self)
        shortcut.activated.connect(lambda:
            self.filter_box.setFocus(Qt.ShortcutFocusReason))

        # TODO: Implement the clear() slot and textChanged(QString) signal
