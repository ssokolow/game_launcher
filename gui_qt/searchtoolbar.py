"""Implementation of promoted search toolbar widget for Qt Designer"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

# pylint: disable=no-name-in-module
from PyQt5.QtCore import QRegExp, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QAction, QActionGroup, QLineEdit, QMenu,
                             QSizePolicy, QToolBar, QToolButton, QWidget)

from .helpers import bind_all_standard_keys, set_action_icon

class SearchField(QLineEdit):
    """Search field which allows Home/End to be delegated"""
    topPressed = pyqtSignal()
    bottomPressed = pyqtSignal()
    lostFocus = pyqtSignal()

    ignored_keys = [
        (Qt.Key_Home, 'topPressed'),
        (QKeySequence.MoveToStartOfDocument, 'topPressed'),
        (Qt.Key_End, 'bottomPressed'),
        (QKeySequence.MoveToEndOfDocument, 'bottomPressed'),
    ]

    def __init__(self, *args, **kwargs):
        super(SearchField, self).__init__(*args, **kwargs)
        self.setClearButtonEnabled(True)

    def keyPressEvent(self, event):
        """Override Home/End (or equivalent) and emit as events"""
        for key, signal in self.ignored_keys:
            if (isinstance(key, QKeySequence.StandardKey) and
                    event.matches(key)):
                getattr(self, signal).emit()
                break
            elif event.key() == key and event.modifiers() == Qt.NoModifier:
                getattr(self, signal).emit()
                break
        else:
            return super(SearchField, self).keyPressEvent(event)

    @pyqtSlot()
    def focus(self):
        self.setFocus(Qt.ShortcutFocusReason)

        # Select any existing text so that users can replace it simply by
        # typing or jump to the beginning or end using the arrow keys.
        # (The latter being important since Home/End or equivalent are
        # forwarded to the results view)
        self.setSelection(0, len(self.text()))

    def focusOutEvent(self, _):
        self.lostFocus.emit()

class SearchToolbar(QToolBar):  # pylint: disable=too-few-public-methods
    """Search toolbar with a few tweaks not possible in pure Qt Designer

    Sources:
     - http://www.setnode.com/blog/right-aligning-a-button-in-a-qtoolbar/
    """

    _text = ''
    regexp = None
    transient = False

    # TODO: Move these to Qt Designer attributes
    DESIRED_WIDTH = 150
    _state = {
        'mode': 'prefix_word',
        'syntax': QRegExp.FixedString,
    }

    escPressed = pyqtSignal()
    topPressed = pyqtSignal()
    nextPressed = pyqtSignal()
    previousPressed = pyqtSignal()
    bottomPressed = pyqtSignal()
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
        self.search_box = self._init_search_widget()
        self.addWidget(self.search_box)

        # Initialize the hotkeys
        self._init_hotkeys()

        # Initialize our regular expression
        self.updateRegExp()

    def _init_search_widget(self):
        """Initialize the SearchField to be used as the actual search box"""
        # Define and configure the actual search field
        search_box = SearchField(self)
        search_box.setMaximumSize(self.DESIRED_WIDTH,
                                  search_box.maximumSize().height())

        # Proxy relevant signals up to where Qt Designer can handle them
        search_box.returnPressed.connect(self.returnPressed.emit)
        search_box.textChanged.connect(self._updateString)
        search_box.topPressed.connect(self.topPressed.emit)
        search_box.bottomPressed.connect(self.bottomPressed.emit)

        # Hook up the handler for hiding when shown transiently
        search_box.lostFocus.connect(self.lostFocus)

        return search_box

    def _init_hotkeys(self):
        """Bind all of the hotkeys to make keyboard navigation comfy"""

        # Hook up Ctrl+F or equivalent
        self.focuskeys = bind_all_standard_keys(QKeySequence.Find, self.focus,
                                                self.parent())

        # Set the placeholder text, including keybinding hints
        key_list = ', '.join(x.key().toString() for x in self.focuskeys)
        self.search_box.setPlaceholderText("Search... ({})".format(key_list))
        self.search_box.setToolTip("Type here to filter displayed results.\n\n"
                        "Hotkeys: {}, Ctrl+L\n\n"
                        "Hotkeys will continue to work with this toolbar "
                        "hidden\n and the toolbar will re-hide when it loses"
                        "focus.".format(key_list))

        # Given its position and role in the workflow, intuition may label it
        # as a navigation bar, so bind Ctrl+L too.
        self.focuskeys += bind_all_standard_keys(Qt.CTRL + Qt.Key_L,
                                                 self.focus, self.parent())

        # Hook up signal for "focus main view without running selected" (Esc)
        esc = getattr(QKeySequence, 'Cancel', Qt.Key_Escape)
        bind_all_standard_keys(esc, self.escPressed.emit, self.search_box,
                               Qt.WidgetWithChildrenShortcut)

        # Hook up signals for previous/next result requests (Up/Down arrows)
        bind_all_standard_keys(QKeySequence.MoveToPreviousLine,
                               self.previousPressed.emit, self.search_box,
                               Qt.WidgetWithChildrenShortcut)
        bind_all_standard_keys(QKeySequence.MoveToNextLine,
                               self.nextPressed.emit, self.search_box,
                               Qt.WidgetWithChildrenShortcut)

    def _init_settings_dropdown(self):
        """Initialize the dropdown button for configuring search"""
        # Build the menu
        menu = QMenu("Search Options", self)
        menu.setToolTipsVisible(True)
        self._build_menu_group(menu, "Match Mode", (
            ('&Prefix', {'mode': 'prefix'},
                'Match titles beginning with the given string'),
            ('Prefix (&Any Word)', {'mode': 'prefix_word'},
                'Match titles where the given string appears '
                'either at the beginning or after a space'),
            ('&Substring', {'mode': 'substring'},
                'Match titles where the given string appears '
                'anywhere... even within a word.')))
        self._build_menu_group(menu, "Syntax", (
            ('&Literal', {'syntax': QRegExp.FixedString},
                'Match search text as-is'),
            ('&Wildcard', {'syntax': QRegExp.Wildcard},
                'Treat the following characters as placeholders:\n\n'
                '? will match exactly one character\n'
                '* will match zero or more characters'),
            ('&RegExp', {'syntax': QRegExp.RegExp2},
                'Treat the search string as a regular expression '
                'using the QRegExp syntax.')))

        # Set up the action for displaying the menu
        action = QAction(menu.title(), self)
        set_action_icon(action, 'search')
        action.setToolTip("Configure search behaviour")
        # TODO: Come up with a keyboard shortcut to trigger this menu which
        # doesn't conflict with any QKeySequence:StandardKey bindings I want

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
        for title, state, tooltip in entries:
            item = modeGroup.addAction(title)
            item.setToolTip(tooltip)
            item.setCheckable(True)
            menu.addAction(item)

            # Set the buttons to match the default state
            if all(state[x] == self._state[x] for x in state):
                item.setChecked(True)

            item.toggled.connect(lambda chek, state=state:
                self._updateState(chek, state))

    def _updateString(self, text):
        """Handler for self.search_box.textChanged"""
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
        elif re_mode == 'prefix_word':
            re_str = r'\b' + re_str

        self.regexp = QRegExp(re_str, Qt.CaseInsensitive, QRegExp.RegExp2)
        self.regexpChanged.emit(self.regexp)

    @pyqtSlot()
    def clear(self):
        """Proxy the clear() slot up to where Qt Designer can work with it"""
        self.search_box.clear()

    @pyqtSlot()
    def focus(self):
        """Proxy the focus() slot up and add a show()"""
        if not self.isVisible():
            self.show()
            self.transient = True

        self.search_box.focus()

    def lostFocus(self):
        """Clear and re-hide if we were hidden when a Ctrl+F/Ctrl+L arrived"""
        if self.transient:
            self.clear()
            self.hide()
            self.transient = False
