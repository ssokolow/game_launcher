"""Context menu for game entries"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QDir, QProcess, QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QMenu

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
            lambda triggered=None, cmd=cmd: self.run_cmd(cmd))

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

    def run_cmd(self, launcher):
        """Run the given program via QProcess"""
        command = launcher.get_command()

        # TODO: Hook up signals for better feedback
        process = QProcess(self)
        process.setWorkingDirectory(command['path'])
        process.start(command['args'][0], command['args'][1:])

    @pyqtSlot()
    def open_folder(self):
        """Callback to open the game's install folder in their file manager"""
        QDesktopServices.openUrl(QUrl.fromLocalFile(
            QDir(self.entry.base_path).absolutePath()))
