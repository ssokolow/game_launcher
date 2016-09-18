"""Implementation of promoted search toolbar widget for Qt Designer"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QRegExp, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QAction, QActionGroup, QLineEdit, QMenu,
                             QSizePolicy, QToolBar, QToolButton, QWidget)

from .helpers import bind_all_standard_keys, set_action_icon

class SearchToolbar(QToolBar):  # pylint: disable=too-few-public-methods
    """Search toolbar with a few tweaks not possible in pure Qt Designer

    Sources:
     - http://www.setnode.com/blog/right-aligning-a-button-in-a-qtoolbar/
    """

    _text = ''
    regexp = None

    # TODO: Move these to Qt Designer attributes
    DESIRED_WIDTH = 150
    _state = {
        'mode': 'keyword',
        'syntax': QRegExp.FixedString,
    }

    nextPressed = pyqtSignal()
    previousPressed = pyqtSignal()
    returnPressed = pyqtSignal()
    regexpChanged = pyqtSignal('QRegExp')

    def __init__(self, *args, **kwargs):
        super(SearchToolbar, self).__init__(*args, **kwargs)
        self._text = ''
        self._state = self._state.copy()

        # Use a spacer to right-align the size-limited field
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(spacer)

        # Define and configure the settings dropdown
        self.dropdown = self._init_settings_dropdown()
        self.addWidget(self.dropdown)

        # Define and configure the actual search field
        self.filter_box = self._init_search_widget()
        self.addWidget(self.filter_box)

        # Initialize our regular expression
        self.updateRegExp()

    def _init_search_widget(self):
        """Initialize the QLineEdit to be used as the actual search box"""
        # Define and configure the actual search field
        filter_box = QLineEdit(self)
        filter_box.setClearButtonEnabled(True)
        filter_box.setMaximumSize(self.DESIRED_WIDTH,
                                  filter_box.maximumSize().height())

        # Proxy relevant signals up to where Qt Designer can handle them
        filter_box.returnPressed.connect(self.returnPressed.emit)
        filter_box.textChanged.connect(self._updateString)

        # Hook up Ctrl+F or equivalent
        hotkeys = bind_all_standard_keys(QKeySequence.Find, lambda:
                filter_box.setFocus(Qt.ShortcutFocusReason), self)

        # Set the placeholder text, including keybinding hints
        filter_box.setPlaceholderText("Search... ({})".format(
            ', '.join(x.key().toString() for x in hotkeys)))

        # Hook up signals for previous/next result requests (Up/Down arrows)
        bind_all_standard_keys(QKeySequence.MoveToPreviousLine,
                               self.previousPressed.emit, filter_box,
                               Qt.WidgetWithChildrenShortcut)
        bind_all_standard_keys(QKeySequence.MoveToNextLine,
                               self.nextPressed.emit, filter_box,
                               Qt.WidgetWithChildrenShortcut)
        return filter_box

    def _init_settings_dropdown(self):
        """Initialize the dropdown button for configuring search"""
        # Set up the action for displaying the menu
        action = QAction('Filter Options', self)
        set_action_icon(action, 'search')
        action.setToolTip("Configure filter behaviour")
        action.setShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_F))

        # Build the menu
        menu = QMenu("Filter Settings", self)
        self._build_menu_group(menu, "Match Mode", (
            ('Prefix', {'mode': 'prefix'}),
            ('Keyword', {'mode': 'keyword'}),
            ('Substring', {'mode': 'substring'})))
        self._build_menu_group(menu, "Syntax", (
            ('Literal', {'syntax': QRegExp.FixedString}),
            ('Wildcard', {'syntax': QRegExp.Wildcard}),
            ('RegExp', {'syntax': QRegExp.RegExp2})))

        # Wrap it in a QToolButton so we can setPopupMode
        button = QToolButton(self)
        button.setDefaultAction(action)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setMenu(menu)

        return button

    def _build_menu_group(self, menu, section, entries):
        """Helper to simplify adding action groups"""
        menu.addSection(section)
        modeGroup = QActionGroup(menu)
        modeGroup.setExclusive(True)
        for title, state in entries:
            item = modeGroup.addAction(title)
            item.setCheckable(True)
            menu.addAction(item)

            # Set the buttons to match the default state
            if all(state[x] == self._state[x] for x in state):
                item.setChecked(True)

            item.toggled.connect(lambda chek, state=state:
                self._updateState(chek, state))

    def _updateString(self, text):
        """Handler for self.filter_box.textChanged"""
        self._text = text
        self.updateRegExp()

    def _updateState(self, checked, state):
        """Handler for _build_menu_group toggled signals"""
        if checked:
            self._state.update(state)
            self.updateRegExp()

    def updateRegExp(self):
        """Common code for updating the QRegExp in response to changes"""
        re_str = self._text
        re_syntax = self._state['syntax']
        re_mode = self._state['mode']

        # Manually convert to RegExp so we can implement our fancy matching
        if re_syntax == QRegExp.FixedString:
            re_str = QRegExp.escape(re_str)
        if re_syntax == QRegExp.Wildcard:
            re_str = QRegExp.escape(re_str)
            re_str = re_str.replace(r'\?', '.').replace(r'\*', '.*')

        # Actually implement fancy matching
        if re_mode == 'prefix':
            re_str = '^' + re_str
        elif re_mode == 'keyword':
            re_str = r'\b' + re_str

        self.regexp = QRegExp(re_str, Qt.CaseInsensitive, QRegExp.RegExp2)
        self.regexpChanged.emit(self.regexp)


    @pyqtSlot()
    def clear(self):
        """Proxy the clear() slot up to where Qt Designer can work with it"""
        self.filter_box.clear()
        # TODO: Test this

