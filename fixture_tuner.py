#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Simple 'get SOMETHING written' experiment into generating test data
for the fallback game provider.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"
__version__ = '0.0pre0'

import json, logging, os, sys
from src.game_providers.fallback import get_games, GAMES_DIRS
log = logging.getLogger(__name__)

# pylint: disable=import-error
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileSystemModel,
                             QStyledItemDelegate)
from PyQt5.uic import loadUi

actions_all = (
    ('', ''),
    ('ignore', 'Ignored'),
)

actions_dir = (
    ('recurse', 'Recurse'),
    ('base_dir', 'Base Install Path'),
)

actions_file = (
    ('installer', 'Installer'),
    ('icon', 'Icon'),
    ('launcher', 'Launcher'),
    # TODO: Replace 'launcher' with all of the actual launcher roles
)

actions_exe = (
    ('launcher+icon', 'Launcher + Icon'),
)


class ActionDelegate(QStyledItemDelegate):
    """Item delegate to provide a dropdown action selector for paths"""
    # pylint: disable=super-on-old-class
    def __init__(self, model):
        super(ActionDelegate, self).__init__()
        self.model = model

    # pylint: disable=unused-argument
    def createEditor(self, parent, option, index):  # NOQA
        editor = QComboBox(parent)

        path = self.model.filePath(index)
        if os.path.isdir(path):
            actions = actions_all + actions_dir
        else:
            actions = actions_all + actions_file
            if os.path.splitext(path)[1].lower() in ('.exe', '.jar'):
                actions += actions_exe

        for key, label in actions:
            editor.addItem(label, key)
        return editor

    # pylint: disable=no-self-use
    def setEditorData(self, editor, index):  # NOQA
        idx = editor.findText(index.data(Qt.DisplayRole))
        editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):  # NOQA
        idx = editor.currentIndex()
        model.setData(index, editor.itemText(idx), Qt.DisplayRole)
        model.setData(index, editor.itemData(idx), Qt.UserRole)

    def updateEditorGeometry(self, editor, option, index):  # NOQA
        editor.setGeometry(option.rect)

class AnnotatedFilesystemModel(QFileSystemModel):
    # pylint: disable=super-on-old-class
    def __init__(self, metadata=None):
        super(AnnotatedFilesystemModel, self).__init__()
        self.meta = metadata or {}
        self.actions_text = dict(actions_all + actions_dir +
                                 actions_file + actions_exe)

    # pylint: disable=unused-argument,no-self-use
    def columnCount(self, parent=None):  # NOQA
        return 2

    # pylint: disable=super-on-old-class
    def data(self, index, role):
        if not index.isValid():
            return None
        elif index.column() == 1:
            if role == Qt.DisplayRole:
                path = self.filePath(index)  # pylint: disable=no-member
                return self.actions_text[self.meta.get(path, '')]
            else:
                return None
        # TODO: Add some colour-coding or other indication for +x files,
        #       things with extensions that mark them as likely candidates for
        #       icons/executables/etc., and so on.
        return super(AnnotatedFilesystemModel, self).data(index, role)

    def flags(self, index):
        base_flags = super(AnnotatedFilesystemModel, self).flags(index)
        if index.column() == 1:
            base_flags |= Qt.ItemIsEditable
        return base_flags

    # pylint: disable=super-on-old-class
    def headerData(self, section, orientation, role):  # NOQA
        if orientation == Qt.Horizontal:
            if section == 1 and role == Qt.DisplayRole:
                return "Action"
        return super(AnnotatedFilesystemModel, self).headerData(
            section, orientation, role)

    def setData(self, index, value, role):  # NOQA
        if role == Qt.UserRole:
            path = self.filePath(index)  # pylint: disable=no-member
            if value:
                self.meta[path] = value
            elif path in self.meta:
                del self.meta[path]
            return True
        return False

class Application(QApplication):  # pylint: disable=too-few-public-methods
    window, model, view = None, None, None

    def __init__(self, argv):  # pylint: disable=super-on-old-class
        super(Application, self).__init__(argv)

    def init_gui(self):
        with open(os.path.join(os.path.dirname(__file__),
                               'fixture_tuner.ui')) as fobj:
            self.window = loadUi(fobj)

        self.model = AnnotatedFilesystemModel()
        self.model.setRootPath(GAMES_DIRS[0])  # pylint: disable=no-member
        # TODO: Make the entry in GAMES_DIR runtime selectable via a drop-down

        self.view = self.window.treeView
        self.view.setModel(self.model)
        # pylint: disable=no-member
        self.view.setRootIndex(self.model.index(GAMES_DIRS[0]))
        self.view.setItemDelegateForColumn(1, ActionDelegate(self.model))
        self.view.setColumnWidth(0, 300)

def set_conditionally(store, key, value):
    if value and key not in store:
        store[key] = value

def default_fixture(store):
    for entry in get_games():
        set_conditionally(store, entry.base_path, 'base_dir')
        set_conditionally(store, entry.icon, 'icon')
        for launcher in entry.commands:
            set_conditionally(store, launcher.icon, 'icon')
            set_conditionally(store, (launcher.argv or [''])[0], 'launcher')

def write_json(obj, path):
    with open(path, 'w') as fobj:
        json.dump(obj, fobj, indent=2)

def main():
    """The main entry point, compatible with setuptools entry points."""
    from argparse import ArgumentParser
    parser = ArgumentParser(
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_argument('--version', action='version',
            version="%%(prog)s v%s" % __version__)
    parser.add_argument('-v', '--verbose', action="count",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_argument('-q', '--quiet', action="count",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    parser.add_argument('fixture', help='JSON file to load/save')
    # Reminder: %(default)s can be used in help strings.

    args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose - args.quiet, len(log_levels) - 1)
    args.verbose = max(args.verbose, 0)
    logging.basicConfig(level=log_levels[args.verbose],
                        format='%(levelname)s: %(message)s')

    app = Application(sys.argv)
    app.init_gui()

    try:
        with open(args.fixture, 'r') as fobj:
            app.model.meta = json.load(fobj)
    except (IOError, ValueError):
        app.model.meta = {}
    default_fixture(app.model.meta)

    app.window.show()
    app.window.saveButton.clicked.connect(
        lambda: write_json(app.model.meta, args.fixture))
    sys.exit(app.exec_())  # pylint: disable=no-member

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
