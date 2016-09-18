"""Non-widget helpers to work around Qt Designer shortcomings/bugs."""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QAction, QActionGroup, QShortcut

def bind_all_standard_keys(standard_key, handler_cb, parent=None,
                           context=Qt.WindowShortcut):
    """Workaround for Qt apparently only binding the first StandardKey
    when it's fed into QShortcut

    @type standard_key: C{QtGui.QKeySequence.StandardKey}
    @type handler_cb: C{function}
    @type parent: C{QObject}
    @type context: C{QtCore.Qt.ShortcutContext}

    @rtype: C{[QtWidgets.QShortcut]}
    """

    results = []
    for hotkey in QKeySequence.keyBindings(standard_key):
        shortcut = QShortcut(hotkey, parent)
        shortcut.setContext(context)
        shortcut.activated.connect(handler_cb)
        results.append(shortcut)
    return results

def set_action_icon(action, name):
    """Helper for working around Qt's broken QIcon::fromTheme"""
    icon = QIcon.fromTheme(name)

    # Support fallback to more than one filename
    # TODO: Decide on a way to use the Qt fallback mechanism
    #       and support multiple icon resolutions.
    #       (Possibly amending the theme search path somehow?)
    if icon.isNull():
        path_base = os.path.join(os.path.dirname(__file__), name)
        for ext in ('svgz', 'svg' 'png'):
            icon_path = '{}.{}'.format(path_base, ext)
            if os.path.exists(icon_path):
                icon = QIcon(os.path.join(icon_path))
                if not icon.isNull():
                    break
    action.setIcon(icon)

# XXX: Does it do more harm than good to dedupe this against the search code?
def make_action_group(parent, action_names):
    """Helper for cleanly grouping actions by name"""
    group = QActionGroup(parent)
    for action_name in action_names:
        group.addAction(parent.findChild(QAction, action_name))

def unbotch_icons(root, mappings):
    """Fix 'pyuic seems to not load Qt Designer-specified theme icons'

    Basically, a helper to manually amend the config in the code.
    """

    for wid_tuple in mappings:
        set_action_icon(root.findChild(wid_tuple[0], wid_tuple[1]),
                        mappings[wid_tuple])
