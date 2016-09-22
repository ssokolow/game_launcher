"""Non-widget helpers to work around Qt Designer shortcomings/bugs."""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

from PyQt5.QtCore import QModelIndex, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QAction, QActionGroup, QShortcut

from .icon_provider import IconProvider

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
    if isinstance(standard_key, QKeySequence.StandardKey):
        hotkeys = QKeySequence.keyBindings(standard_key)
    else:
        hotkeys = [standard_key]

    for hotkey in hotkeys:
        shortcut = QShortcut(hotkey, parent)
        shortcut.setContext(context)
        shortcut.activated.connect(handler_cb)
        results.append(shortcut)
    return results

def iterate_model(model, parent_idx=None, topdown=True):
    """A generator for depth-first iteration through a QAbstractItemModel.

    Adapted from source at http://stackoverflow.com/q/26040977
    with C{topdown} inspired by the C{os.walk} API.
    """
    if not parent_idx or not parent_idx.isValid():
        parent_idx = QModelIndex()

    if topdown:
        yield parent_idx

    for row in range(0, model.rowCount(parent_idx)):
        for child_idx in iterate_model(model, model.index(row, 0, parent_idx)):
            yield child_idx

    if not topdown:
        yield parent_idx

# TODO: Finish merging this into IconProvider
def set_action_icon(action, name):
    """Helper for working around Qt's broken QIcon::fromTheme"""
    icon = QIcon.fromTheme(name)

    # Support fallback to more than one filename
    # TODO: Decide on a way to use the Qt fallback mechanism
    #       and support multiple icon resolutions.
    #       (Possibly amending the theme search path somehow?)
    if icon.isNull():
        icon = IconProvider.lookup_local(name) or icon
    action.setIcon(icon)

# XXX: Does it do more harm than good to dedupe this against the search code?
def make_action_group(parent, action_names, always_usable=False):
    """Helper for cleanly grouping actions by name

    If always_usable is True, also add them to C{parent} in case their toolbar
    is hidden.
    """
    group = QActionGroup(parent)
    for action_name in action_names:
        action = parent.findChild(QAction, action_name)
        group.addAction(action)
        if always_usable:
            parent.addAction(action)
    return group

def unbotch_icons(root, mappings):
    """Fix 'pyuic seems to not load Qt Designer-specified theme icons'

    Basically, a helper to manually amend the config in the code.
    """

    for wid_tuple in mappings:
        set_action_icon(root.findChild(wid_tuple[0], wid_tuple[1]),
                        mappings[wid_tuple])
