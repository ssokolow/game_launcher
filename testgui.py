#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""[application description here]"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Test GUI for game_launcher"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import logging, os, subprocess, sys
log = logging.getLogger(__name__)

RES_DIR = os.path.dirname(__file__)
ICON_SIZE = 32

# ---=== Begin Imports ===---

from xml.sax.saxutils import escape as xmlescape

from test_providers import get_games
from game_providers.common import GameLauncher

try:
    import pygtk
    pygtk.require("2.0")
except ImportError:
    pass  # Apparently some PyGTK installs are missing this but still work

try:
    import gtk, gtk.gdk, glib  # pylint: disable=import-error
except ImportError:
    sys.stderr.write("Missing PyGTK! Exiting.\n")
    sys.exit(1)

# Present tracebacks as non-fatal errors in the GUI for more user-friendliness
# TODO: In concert with this, I'll probably want some kind of failsafe
#       for re-enabling the Save button if necessary.
from lgogd_uri import gtkexcepthook
gtkexcepthook.enable()

# ---=== Begin Application Class ===---

class Application(object):  # pylint: disable=C0111,R0902
    def __init__(self):
        # Shut up PyLint about defining members in _init_gui
        self.builder = gtk.Builder()
        self.data = None
        self.entries = []
        self.icon_theme = gtk.icon_theme_get_default()

        """Parts of __init__ that should only run in the single instance."""
        # Check for some deps late enough to display a GUI error message
        self.gtkbuilder_load('testgui.glade')
        self.data = self.builder.get_object('store_games')

        self.view = self.builder.get_object("view_games")
        self.view.set_selection_mode(gtk.SELECTION_MULTIPLE)

        self.view.set_text_column(1)
        self.view.set_pixbuf_column(0)

        self.populate_model()

        mainwin = self.builder.get_object('mainwin')
        mainwin.set_title('%s %s' % (mainwin.get_title(), __version__))
        mainwin.show_all()

    def gtkbuilder_load(self, path):
        path = os.path.join(RES_DIR, path)
        self.builder.add_from_file(os.path.join(RES_DIR, path))
        self.builder.connect_signals(self)

    def get_scaled_icon(self, path):
        """@todo: Replace this with something less hacky."""
        if self.icon_theme.has_icon(path):
            return self.icon_theme.load_icon(path, ICON_SIZE, 0)
        elif os.path.exists(path):
            try:
                icon = gtk.gdk.pixbuf_new_from_file(path)
                w, h = icon.get_width(), icon.get_height()

                if w >= h > 32:
                    ratio = w / 32.0
                elif h >= w > 32:
                    ratio = h / 32.0
                else:
                    return icon

                # TODO: Figure out how to tap into GTK's scaled icon generation
                #       and caching
                return icon.scale_simple(int(w / ratio), int(h / ratio),
                                         gtk.gdk.INTERP_BILINEAR)
            except glib.GError:
                # TODO: Broken icon placeholder
                icon = None
        else:
            log.error("BAD ICON: %s", path)
            return None

    def populate_model(self):
        """Populate store_games."""
        # Source: http://faq.pygtk.org/index.py?req=show&file=faq13.043.htp
        self.view.freeze_child_notify()
        self.view.set_model(None)
        self.data.set_default_sort_func(lambda *args: -1)
        self.data.set_sort_column_id(-1, gtk.SORT_ASCENDING)

        self.entries = get_games()

        try:
            for pos, entry in enumerate(self.entries):
                description = "%s (%s)" % (entry.name, ', '.join(entry.provider))
                if entry.description and entry.description != entry.name:
                    description += "\n\n" + xmlescape(entry.description)
                if any(x for x in entry.xdg_categories if x != 'Game'):
                    description += ("\n\nCategories:\n- " + xmlescape(
                                    '\n- '.join([x for x in
                                                 entry.xdg_categories if
                                                 x != 'Game'])))

                self.data.append((
                    self.get_scaled_icon(entry.icon),
                    entry.name,
                    description,
                    pos
                ))
        finally:
            self.data.set_sort_column_id(1, gtk.SORT_ASCENDING)
            self.view.set_model(self.data)
            self.view.thaw_child_notify()

    def gtk_main_quit(self, widget, event):  # pylint: disable=R0201,W0613
        """Helper for Builder.connect_signals"""
        gtk.main_quit()

    def on_view_games_item_activated(self, widget, path):
        self.entries[self.data[path][3]].first_launcher(
            role=GameLauncher.Roles.play).run()
        # TODO: Add some sort of is-running notification to the GUI

    # pylint: disable=no-self-use
    # def on_view_games_key_press_event(self, widget, event):
    #     """Handler for enabling the Delete key"""
    #     if (event.type == gtk.gdk.KEY_PRESS and
    #             event.keyval == gtk.keysyms.Delete):
    #         model, rows = widget.get_selection().get_selected_rows()
    #         rows = [gtk.TreeRowReference(model, x) for x in rows]
    #         for ref in rows:
    #             model.remove(model.get_iter(ref.get_path()))

    # pylint: disable=unused-argument,invalid-name
    def on_view_games_button_press_event(self, widget, event=None):
        """Right-click and Menu button handler for the TreeView.

        Source: http://faq.pygtk.org/index.py?req=show&file=faq13.017.htp
        """
        treeview = self.builder.get_object('view_games')
        if event and event.button == 3:  # Right Click
            evt_btn, evt_time = event.button, event.time
        elif event:                      # Non-right Click
            return None
        elif not event:                  # Menu key on the keyboard
            evt_btn, evt_time = None, None  # TODO: Make sure this works
            cursor = treeview.get_cursor()
            if cursor[0] is None:
                return None

        # Code to handle right-clicking on a non-selected entry
        # Source: http://www.daa.com.au/pipermail/pygtk/2005-June/010465.html
        path = treeview.get_path_at_pos(int(event.x), int(event.y))
        selection = treeview.get_selection()
        rows = selection.get_selected_rows()
        if path[0] not in rows[1]:
            selection.unselect_all()
            selection.select_path(path[0])

        self.builder.get_object("popup_games").popup(
            None, None, None, evt_btn, evt_time)
        return True

    # def on_games_delete_activate(self, _):
    #     """Handler to allow TreeView entry deletion"""
    #     widget = self.builder.get_object('view_games')
    #     model, rows = widget.get_selection().get_selected_rows()
    #     rows = [gtk.TreeRowReference(model, x) for x in rows]
    #     for ref in rows:
    #         model.remove(model.get_iter(ref.get_path()))

def main():
    """The main entry point, compatible with setuptools entry points."""
    from optparse import OptionParser
    parser = OptionParser(version="%%prog v%s" % __version__,
            usage="%prog [options] <gogdownloader URI> ...",
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_option('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_option('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    # Reminder: %default can be used in help strings.

    # Allow pre-formatted descriptions
    parser.formatter.format_description = lambda description: description

    opts, _ = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    opts.verbose = min(opts.verbose - opts.quiet, len(log_levels) - 1)
    opts.verbose = max(opts.verbose, 0)
    logging.basicConfig(level=log_levels[opts.verbose],
                        format='%(levelname)s: %(message)s')

    Application()
    gtk.main()
    gtk.gdk.notify_startup_complete()

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
