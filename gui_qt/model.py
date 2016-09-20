"""Qt Model class to adapt game-handling backend to Qt GUI"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

# TODO: Support per-backend fallback icons (eg. GOG and PlayOnLinux)
# TODO: Now that I have some means of loading fallback icons, I should have
#       each backend bundle a fallback icon (as well as this root fallback)
FALLBACK_ICON = "applications-games"
ICON_SIZE = 64

from PyQt5.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt)

from .icon_provider import IconProvider

icon_provider = IconProvider(FALLBACK_ICON)


class GameListModel(QAbstractTableModel):
    """Qt model class to adapt game-handling backend to Qt Views"""
    def __init__(self, data_list, parent=None):
        super(GameListModel, self).__init__(parent)

        self.games = data_list
        self.icon_size = ICON_SIZE  # TODO: Do this properly
        self.icon_cache = {}  # TODO: Do this properly

    def as_sorted(self):
        model_sorted = QSortFilterProxyModel()
        model_sorted.setDynamicSortFilter(True)
        model_sorted.setSortCaseSensitivity(Qt.CaseInsensitive)
        model_sorted.setFilterCaseSensitivity(Qt.CaseInsensitive)
        model_sorted.setSourceModel(self)
        model_sorted.sort(0, Qt.AscendingOrder)
        return model_sorted

    def columnCount(self, parent):  # pylint: disable=R0201
        if parent and parent.isValid():
            return 0
        return 2

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
                return icon_provider.get_icon(self.games[row].icon,
                                              self.icon_size)
            elif role == Qt.ToolTipRole:
                return self.games[row].summarize()
            # TODO: Add a way to toggle between "The Bridge" and "Bridge, The"
        elif col == 1 and role == Qt.DisplayRole:
            # TODO: Display tiny icons instead
            return ', '.join(x.backend_name for x in self.games[row].provider)

    def flags(self, index):
        """Add ItemNeverHasChildren to the default flags for optimization"""
        flags = Qt.ItemIsSelectable | Qt.ItemNeverHasChildren
        if not getattr(self.games[index.row()], 'is_running', False):
            flags |= Qt.ItemIsEnabled
        return flags

    def headerData(self, section, orientation, role):  # pylint: disable=R0201
        # TODO: Can Qt provide automatic hide/show-able column support?
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return "Title"
            elif section == 1:
                return "Provider"

    def rowCount(self, parent):
        if parent and parent.isValid():
            # Not tree-structured
            return 0
        return len(self.games)
