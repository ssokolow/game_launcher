"""Qt Model class to adapt game-handling backend to Qt GUI"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

# TODO: Support per-backend fallback icons (eg. GOG and PlayOnLinux)
# TODO: Now that I have some means of loading fallback icons, I should have
#       each backend bundle a fallback icon (as well as this root fallback)
FALLBACK_ICON = "applications-games"
ICON_SIZE = 64

# pylint: disable=no-name-in-module,wrong-import-position
from PyQt5.QtCore import (QAbstractItemModel, QAbstractTableModel, QModelIndex,
                          QSortFilterProxyModel, Qt)

from PyQt5_fixes.icon_provider import IconProvider

icon_provider = IconProvider(FALLBACK_ICON)

# -- Proxy Models --

class FunctionalInitMixin(object):
    """Mixin to provide a wrap(sourceModel) class method to proxy models"""
    @classmethod
    def wrap(cls, sourceModel):
        """Wrapper for a more functional init style"""
        model = cls()
        model.setSourceModel(sourceModel)
        return model

class BasicSortFilterProxyModel(QSortFilterProxyModel, FunctionalInitMixin):
    """A subclass which encapsulates the desired configuration tweaks"""
    def __init__(self, *args, **kwargs):
        super(BasicSortFilterProxyModel, self).__init__(*args, **kwargs)
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def setSourceModel(self, model):
        """A wrapper for setSourceModel which ensures proper sort indication"""
        super(BasicSortFilterProxyModel, self).setSourceModel(model)

        # Force the header sort indicator to match the data so the initial
        # click won't be a no-op.
        self.sort(0, Qt.AscendingOrder)

# -- Non-Proxy Models --

class CategoriesModel(QAbstractItemModel):
    ICON_SIZE = 16

    def __init__(self, sourceModel, parent=None):
        super(CategoriesModel, self).__init__(parent)

        self._source = sourceModel
        self._regenerate()

        for signal in ('dataChanged', 'layoutChanged', 'modelReset',
                       'rowsInserted', 'rowsMoved', 'rowsRemoved'):
            getattr(self._source, signal).connect(self._regenerate)

    # TODO: Use a less sledgehammer-y approach
    def _regenerate(self):
        self.beginResetModel()
        self.provider_by_name = {}
        self.game_by_provider = {}

        # Reverse the game->providers mapping for each game
        for row in range(0, self._source.rowCount()):
            # TODO: Write a custom delegate for the Provider column so I don't
            # need to stringify the provider list before storing it in there
            # and can use it from here.
            index = self._source.index(row, 0)
            entry = self._source.data(index, Qt.UserRole)

            for provider in entry.provider:
                self.provider_by_name[provider.backend_name] = provider
                self.game_by_provider.setdefault(provider, set()).add(index)

        self.ordering = list(sorted(self.provider_by_name.keys(),
                                    key=lambda x: x.lower()))
        self.endResetModel()

    def columnCount(self, _):  # pylint: disable=no-self-use
        """This model always has one column"""
        return 1

    def data(self, index, role):
        if (not index.isValid()) or index.row() >= len(self.ordering):
            return None

        name = self.ordering[index.row()]
        provider = self.provider_by_name[name]
        if role == Qt.UserRole:
            return self.game_by_provider[provider]
        elif index.column() == 0:
            if role == Qt.DisplayRole:
                return provider.backend_name
            elif role == Qt.DecorationRole:
                return icon_provider.get_icon(provider.default_icon,
                                              self.ICON_SIZE)

    def flags(self, index):
        # TODO: Add ItemNeverHasChildren to leaf nodes
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def index(self, row, column, parent=None):  # pylint: disable=W0613
        return self.createIndex(row, column)

    def parent(self, index):  # pylint: disable=unused-argument,R0201
        return QModelIndex()  # Top-level

    def rowCount(self, parent):
        if parent and parent.isValid():
            # Not tree-structured (yet)
            return 0
        return len(self.ordering)

class GameListModel(QAbstractTableModel):
    """Qt model class to adapt game-handling backend to Qt Views"""
    def __init__(self, data_list, parent=None):
        super(GameListModel, self).__init__(parent)

        self.games = data_list
        self.icon_size = ICON_SIZE  # TODO: Do this properly
        self.icon_cache = {}  # TODO: Do this properly

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
