from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QLineEdit, QToolBar, QSizePolicy, QWidget

class SearchToolbar(QToolBar):
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
