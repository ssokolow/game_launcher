"""Qt Model class to adapt game-handling backend to Qt GUI"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

# TODO: Support per-backend fallback icons (eg. GOG and PlayOnLinux)
# TODO: Now that I have some means of loading fallback icons, I should have
#       each backend bundle a fallback icon (as well as this root fallback)
FALLBACK_ICON = "applications-games"
ICON_SIZE = 64

import os

from PyQt5.QtCore import QAbstractTableModel, QSize, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QIcon

from xdg.IconTheme import getIconPath

class GameListModel(QAbstractTableModel):
    """Qt model class to adapt game-handling backend to Qt Views"""
    def __init__(self, data_list):
        self.games = data_list
        self.icon_size = QSize(ICON_SIZE, ICON_SIZE)  # TODO: Do this properly
        self.icon_cache = {}  # TODO: Do this properly

        super(GameListModel, self).__init__()

    def as_sorted(self):
        model_sorted = QSortFilterProxyModel()
        model_sorted.setDynamicSortFilter(True)
        model_sorted.setSortCaseSensitivity(Qt.CaseInsensitive)
        model_sorted.setFilterCaseSensitivity(Qt.CaseInsensitive)
        model_sorted.setSourceModel(self)
        model_sorted.sort(0, Qt.AscendingOrder)
        return model_sorted

    def rowCount(self, parent):
        if parent and parent.isValid():
            # Not tree-structured
            return 0
        return len(self.games)

    def columnCount(self, parent):
        if parent and parent.isValid():
            return 0
        return 2

    def flags(self, index):
        """Add ItemNeverHasChildren to the default flags for optimization"""
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemNeverHasChildren

    # TODO: Move icon-related stuff into its own provider class
    def ensure_icon_size(self, icon):
        """Workaround to QIcon not offering an upscale to match' mode"""
        if not icon:
            return

        desired = self.icon_size
        offered = icon.actualSize(desired)

        if (offered.width() < desired.width() and
                offered.height() < desired.height()):
            # TODO: Port over smart upscaling algorithm
            pixmap = icon.pixmap(desired).scaled(desired,
                Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.addPixmap(pixmap)

            # Hack around fromTheme producing a QIcon which ignores addPixmap
            if icon and icon.actualSize(desired) != desired:
                old_icon = icon
                icon = QIcon(pixmap)
                for size in old_icon.availableSizes():
                    icon.addPixmap(old_icon.pixmap(size))

        return icon

    # TODO: Do this properly
    def get_icon(self, icon_name):
        """Workaround for Qt not implementing a fallback chain in fromTheme"""
        # Always let the cache service requests first
        if icon_name in self.icon_cache:
            return self.icon_cache[icon_name]

        # Skip right to the fallback if it's None or an empty string
        if icon_name:
            # Give Qt the opportunity to make a fool out of itself
            if os.path.isfile(icon_name):
                icon = QIcon(icon_name)
            else:
                icon = QIcon.fromTheme(icon_name)

            # Resort to PyXDG to walk the fallback chain properly
            # TODO: Better resolution handling
            if not icon or icon.isNull():
                icon = QIcon(getIconPath(icon_name, ICON_SIZE,
                                         theme=QIcon.themeName()))
        else:
            icon = None

        # If we still couldn't get a result, retrieve the fallback icon in a
        # way which will allow a cache entry here without duplication
        if not icon or icon.isNull() and icon_name != FALLBACK_ICON:
            icon = self.get_icon(FALLBACK_ICON)

        # Populate the cache
        icon = self.ensure_icon_size(icon)
        self.icon_cache[icon_name] = icon
        return icon

    def headerData(self, section, orientation, role):
        # TODO: Can Qt provide automatic hide/show-able column support?
        if role == Qt.DisplayRole:
            if section == 0:
                return "Title"
            elif section == 1:
                return "Provider"

    def data(self, index, role):
        if (not index.isValid()) or index.row() >= len(self.games):
            return None

        # TODO: Make the game resolution order deterministic between the two
        #       copies of Race The Sun that I have installed.
        #       (Python 2.x with GTK+ finds 1.42 first and Python 3.x with Qt
        #        finds 1.10 first and the two versions have different icons
        #        so that's how I noticed.)
        row = index.row()
        col = index.column()

        if role == Qt.UserRole:
            return self.games[row]
        elif col == 0:
            if role == Qt.DisplayRole:
                return self.games[row].name
            elif role == Qt.DecorationRole:
                return self.get_icon(self.games[row].icon)
            elif role == Qt.ToolTipRole:
                return self.games[row].summarize()
            # TODO: Add a way to toggle between "The Bridge" and "Bridge, The"
        elif col == 1 and role == Qt.DisplayRole:
            return ', '.join(self.games[row].provider)
