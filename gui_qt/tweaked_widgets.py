from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import (QLineEdit, QToolBar, QSizePolicy, QTreeView,
                             QWidget)

class NarrowerTreeView(QTreeView):
    """A subclass of QTreeView which works around Qt Designer's inability to
    set default sizes for QDockWidget.

    Source:
        http://stackoverflow.com/a/13715893
    """
    def sizeHint(self):
        return QSize(150, 75)

class SearchToolbar(QToolBar):
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
        self.filter_box.setMaximumSize(self.DESIRED_WIDTH,
            self.filter_box.maximumSize().height())
        self.addWidget(self.filter_box)

        # TODO: Implement the clear() slot and textChanged(QString) signal
