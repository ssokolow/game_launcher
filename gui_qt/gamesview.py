"""Implementation of promoted stacked widget for Qt Designer"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QDir, QUrl, Qt, pyqtSlot
from PyQt5.QtGui import QDesktopServices, QCursor
from PyQt5.QtWidgets import QListView, QMenu, QStackedWidget, QTableView

from src.util.executables import Roles

class GameContextMenu(QMenu):
    """Context menu for an entry in the games list
    TODO: The popup menu should include:
          - A submenu for selecting which subentry is default (double-click)
          - An option to merge the selected entries which is conditional
            on multiple entries actually being selected.
          - An option to split the selected entry's subentries into entries.
          - An option to change the icon which opens a dialog box with...
              - A preview with a scale slider
              - A "Pick Icon..." button which causes the system to scan the
                game's container (folder, WINEPREFIX, etc.) and display an
                icon picker with all found icons.
                - I'll want to examine gExtractWinIcons to figure out what
                  it's doing that I'm not when using wrestool directly.
              - A "Browse Icon..." button which calls up an open dialog.
              - Some kind of cropper to help un-border things like
                GOG's rounded icons.
              - A checkbox to auto-remove a solid-colour background
                like in the icons for Reus, Vessel, Uplink, Escape Goat 2,
                and possibly Beatblasters III and Not The Robots, but not
                Super Meat Boy, Shadowgrounds, Dear Esther, or Antichamber.
              - Some kind of matte adjustment control for upscaling
              - A dropdown to override the choice of scaling algorithm
                on a per-icon basis.
          - A preferences panel which provides...
              - A means of setting launch wrappers like pasuspender
              - A means of setting custom arguments to the game
              - A means of editing subentries?
              - A dropdown to select an antimicro profile to enable on launch
              - Checkboxes to enable or disable LD_PRELOAD hooks
          - ...and what else?
    """
    def __init__(self, parent, entry):
        super(GameContextMenu, self).__init__(parent)
        self.entry = entry

        self._add_launchers()
        self.addSeparator()
        self.addAction("Open Install Folder", self.open_folder).setEnabled(
            bool(entry.base_path))
        self.addAction("Rename...").setEnabled(False)
        self.addAction("Hide").setEnabled(False)

    def _add_action(self, cmd):
        """Code split out of _add_launchers for clarity"""
        # TODO: Accelerator keys
        # TODO: Add an "Are you sure?" dialog for install/uninstall
        # TODO: Use QProcess so we can have a throbber and the like
        action = self.addAction(self._entry_launcher_name(self.entry, cmd),
                                lambda triggered=None, cmd=cmd: cmd.run())

        # TODO: Actually use a customizable default setting
        if cmd == self.entry.default_launcher:
            font = action.font()
            font.setBold(True)
            action.setFont(font)

    def _add_launchers(self):
        """Add the actions which vary from entry to entry

        (As opposed to simply being enabled or disabled)
        """
        # TODO: Move all of this frontend-agnostic ordering code to the backend
        # TODO: If there's more than one install prefix detected, group and
        #  provide section headers.
        #  (eg. multiple versions of the same game installed in parallel)
        play, other = [], []
        default_cmd = self.entry.default_launcher
        for command in list(sorted(self.entry.commands,
                            key=lambda x: (x != default_cmd, x.role, x.name))):
            if command.role == Roles.play:
                play.append(command)
            else:
                other.append(command)

        for cmd in play:
            self._add_action(cmd)
        if play and other:
            self.addSeparator()
        for cmd in other:
            self._add_action(cmd)

    def _entry_launcher_name(self, entry, cmd):
        # TODO: Move this into the frontend-agnostic launcher code where it
        # belongs
        if cmd.name != entry.name:
            return cmd.name
        elif cmd.role != Roles.unknown:
            return cmd.role.name.title()
        else:
            return 'Play'

    @pyqtSlot()
    @pyqtSlot(bool)
    def open_folder(self, triggered=None):
        """Callback to open the game's install folder in their file manager"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(
            QDir(self.entry.base_path).absolutePath()))

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

        # Hook up double-click/enter/right-click/menukey handlers
        for view in (self.listview, self.tableview):
            view.activated.connect(self.launchEntry)
            view.customContextMenuRequested.connect(self.context_menu_for)

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

    # TODO: The popup menu should include:
    #       - A submenu for selecting which subentry is default (double-click)
    #       - An option to merge the selected entries which is conditional
    #         on multiple entries actually being selected.
    #       - An option to split the selected entry's subentries into entries.
    #       - An option to change the icon which opens a dialog box with...
    #           - A preview with a scale slider
    #           - A "Pick Icon..." button which causes the system to scan the
    #             game's container (folder, WINEPREFIX, etc.) and display an
    #             icon picker with all found icons.
    #             - I'll want to examine gExtractWinIcons to figure out what
    #               it's doing that I'm not when using wrestool directly.
    #           - A "Browse Icon..." button which calls up an open dialog.
    #           - Some kind of cropper to help un-border things like
    #             GOG's rounded icons.
    #           - A checkbox to auto-remove a solid-colour background
    #             like in the icons for Reus, Vessel, Uplink, Escape Goat 2,
    #             and possibly Beatblasters III and Not The Robots, but not
    #             Super Meat Boy, Shadowgrounds, Dear Esther, or Antichamber.
    #           - Some kind of matte adjustment control for upscaling
    #           - A dropdown to override the choice of scaling algorithm
    #             on a per-icon basis.
    #       - A preferences panel which provides...
    #           - A means of setting launch wrappers like pasuspender
    #           - A means of setting custom arguments to the game
    #           - A means of editing subentries?
    #           - A dropdown to select an antimicro profile to enable on launch
    #           - Checkboxes to enable or disable LD_PRELOAD hooks
    #       - ...and what else?
    # pylint: disable=invalid-name
    def context_menu_for(self, pos):
        """Generate and return a context menu for the given position"""
        entry = self.model.data(self.currentView().indexAt(pos), Qt.UserRole)
        if entry:
            GameContextMenu(self, entry).popup(QCursor.pos())

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
