#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""[application description here]"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__appname__ = "Test GUI for game_launcher"
__version__ = "0.0pre0"
__license__ = "GNU GPL 3.0 or later"

import logging, os, sys
log = logging.getLogger(__name__)

RES_DIR = os.path.dirname(__file__)
ICON_SIZE = 64

# TODO: Support per-backend fallback icons (eg. GOG and PlayOnLinux)
FALLBACK_ICON = "applications-games"

# ---=== Begin Imports ===---

from xml.sax.saxutils import escape as xmlescape

# TODO: Decide on a name for the project and rename "src"
from src.game_providers import get_games

try:
    import pygtk
    pygtk.require("2.0")
except ImportError:
    pass  # Apparently some PyGTK installs are missing this but still work

try:
    import gtk, gtk.gdk, glib, pango
except ImportError:
    sys.stderr.write("Missing PyGTK! Exiting.\n")
    sys.exit(1)

# TODO: Uncomment this once I'm no longer debugging
# Present tracebacks as non-fatal errors in the GUI for more user-friendliness
# from lgogd_uri import gtkexcepthook
# gtkexcepthook.enable()

# ---=== Begin Application Class ===---

class Application(object):  # pylint: disable=C0111,R0902
    def __init__(self):
        self.builder = gtk.Builder()
        self.icon_theme = gtk.icon_theme_get_default()

        """Parts of __init__ that should only run in the single instance."""
        # Check for some deps late enough to display a GUI error message
        self.gtkbuilder_load('testgui.glade')
        self.data = self.builder.get_object('store_games')

        self.view = self.builder.get_object("view_games")
        self.view.set_selection_mode(
            gtk.SELECTION_MULTIPLE)

        # Apparently Glade doesn't let you set these in the XML for IconView
        self.view.set_text_column(1)
        self.view.set_pixbuf_column(0)

        self.entries = get_games()
        self.populate_model(self.entries)

        self.mainwin = self.builder.get_object('mainwin')
        self.mainwin.set_title('%s %s' %
                               (self.mainwin.get_title(), __version__))
        self.mainwin.show_all()

    def gtkbuilder_load(self, path):
        """Shorthand wrapper for all steps of loading a GtkBuilder file"""
        path = os.path.join(RES_DIR, path)
        self.builder.add_from_file(os.path.join(RES_DIR, path))
        self.builder.connect_signals(self)

    def _ensure_good_upscales(self, icon_name, target_size):
        """Mitigate scaling blur for icons smaller than 32px
        (By using pixel doubling/tripling to give them a more retro look)
        """
        iinfo = self.icon_theme.lookup_icon(icon_name, target_size,
                        gtk.ICON_LOOKUP_USE_BUILTIN)
        if iinfo is None:
            return None
        base_size = iinfo.get_base_size()

        # For icons smaller than 32px use pixel doubling to add some upscales
        # (Otherwise, 16px icons are unacceptably blurry)
        # Also, add some explicitly doubled versions for icons which refuse to
        # scale to force scaling.
        # TODO: I'll have to figure out how to workaround PlayOnLinux's
        #       crappy 16->32 upscaling
        icon = self.icon_theme.load_icon(icon_name, base_size, 0)
        w, h = icon.get_width(), icon.get_height()

        # Inject larger versions using INTERP_NEAREST at integer scales up to
        # but not including the target size (but at least once for any icons
        # below 32px). It provides a good compromise between the jagginess of
        # raw pixel doubling and the extreme blur of heavy interpolation.
        scale = 2
        while base_size * scale < max(target_size, 32 * 2):
            isize = max(w, h)
            log.debug("%s: %s -> %s", icon_name, isize, base_size * scale)

            gtk.icon_theme_add_builtin_icon(icon_name, isize * scale,
                icon.scale_simple(w * scale, h * scale,
                    gtk.gdk.INTERP_NEAREST))
            scale += 1

    @staticmethod
    def _ensure_dimensions(icon, target_size, threshold=16):
        """Workaround used by L{get_scaled_icon} to deal with a bug where
           GTK+ returns a 32px icon for DOSBox when 64px is requested.

           If the largest dimension of the given image is at least C{threshold}
           pixels different from the target size, rescale to the target size
           using C{INTERP_HYPER} (the slowest and most accurate scaling
           algorithm... but I've only ever seen GTK+ ignore a size request for
           an icon once, so this function should normally not do any scaling.
           """
        w, h = icon.get_width(), icon.get_height()
        isize = max(w, h)

        if abs(target_size - isize) >= threshold:
            factor = target_size / h if w < h else target_size / w
            return icon.scale_simple(int(w * factor), int(h * factor),
                                     gtk.gdk.INTERP_HYPER)
        else:
            return icon

    def get_scaled_icon(self, path, size):
        """Interpret a raw Icon value from a .desktop and return a good icon

        (Employs L{_ensure_good_upscales} to minimize blurrying tiny icons)

        @todo: Consider some kind of autocropping for things like Ultratron
               where they matted a perfectly good square icon on a rectangular
               white background.
        """
        if path is None:
            return None

        # Inject non-theme icon paths as builtins for consistent lookup
        if os.path.exists(path) and not self.icon_theme.has_icon(path):
            icon = gtk.gdk.pixbuf_new_from_file(path)
            w, h = icon.get_width(), icon.get_height()
            isize = max(w, h)

            gtk.icon_theme_add_builtin_icon(path, isize, icon)

        # TODO: Deduplicate this code as much as possible
        try:
            self._ensure_good_upscales(path, size)
            icon = self.icon_theme.load_icon(path, size, 0)
            if not (size == icon.get_width() == icon.get_height()):
                log.debug("%s: %s != %s != %s" %
                      (path, size, icon.get_width(), icon.get_height()))
            return self._ensure_dimensions(icon, size)
        except (AttributeError, glib.GError):
            log.error("BAD ICON: %s", path)
            try:
                return self._ensure_dimensions(
                    self.icon_theme.load_icon(FALLBACK_ICON, size, 0))
            except glib.GError, err:
                log.error("Error while loading fallback icon: %s", err)
        return None

    # TODO: The popup menu should include:
    #       - A submenu for selecting which subentry is default (double-click)
    #       - An option to merge the selected entries which is conditional
    #         on multiple entries actually being selected.
    #       - An option to split the selected entry's subentries into entries.
    #       - An option to change the icon which opens a dialog box with...
    #           - A preview with a scale slider
    #           - A "Pick Icon..." button which causes the system to scan the
    #             game's container (folder, WINEPREFIX, etc.) and display an
    #             icon picker with all found icons.
    #             - I'll want to examine gExtractWinIcons to figure out what
    #               it's doing that I'm not when using wrestool directly.
    #           - A "Browse Icon..." button which calls up an open dialog.
    #           - Some kind of cropper to help un-border things like
    #             GOG's rounded icons.
    #           - A checkbox to auto-remove a solid-colour background
    #             like in the icons for Reus, Vessel, Uplink, Escape Goat 2,
    #             and possibly Beatblasters III and Not The Robots, but not
    #             Super Meat Boy, Shadowgrounds, Dear Esther, or Antichamber.
    #           - Some kind of matte adjustment control for upscaling
    #           - A dropdown to override the choice of scaling algorithm
    #             on a per-icon basis.
    #       - A preferences panel which provides...
    #           - A means of setting launch wrappers like pasuspender
    #           - A means of setting custom arguments to the game
    #           - A means of editing subentries?
    #           - A dropdown to select an antimicro profile to enable on launch
    #           - Checkboxes to enable or disable LD_PRELOAD hooks
    #       - ...and what else?
    # pylint: disable=invalid-name
    def make_popup_for(self, pos):
        """Generate and return a context menu for the given entry index"""
        popup = gtk.Menu()
        entry = self.entries[self.data[pos][3]]

        default_cmd = entry.default_launcher
        for cmd in sorted(entry.commands,
                          key=lambda x: (x != default_cmd, x.role, x.name)):
            # TODO: Move this into the frontend agnostic code
            # TODO: Use the role name, falling back to Play only if unknown
            # TODO: Sort by role
            # TODO: Put a separator between the Play links and the inst/uninst
            name = cmd.name if cmd.name != entry.name else 'Play'

            # TODO: Add an "Are you sure?" dialog for install/uninstall
            item = gtk.MenuItem(name)
            item.connect('activate', lambda _, cmd=cmd: cmd.run())
            popup.add(item)

            # TODO: Actually use a customizable default setting
            if cmd == default_cmd:
                attrs = pango.AttrList()
                attrs.insert(pango.AttrWeight(600, end_index=len(name)))
                item.get_child().set_attributes(attrs)

        popup.add(gtk.SeparatorMenuItem())

        mi_rename = gtk.MenuItem("Rename...")
        mi_rename.connect('activate', self.on_mi_rename_activate, pos)
        popup.add(mi_rename)

        mi_hide = gtk.MenuItem("Hide")
        mi_hide.connect('activate', self.on_mi_hide_activate, pos)
        popup.add(mi_hide)
        popup.show_all()
        return popup

    def populate_model(self, src_list):
        """Populate store_games."""
        # Source: http://faq.pygtk.org/index.py?req=show&file=faq13.043.htp
        self.view.freeze_child_notify()
        self.view.set_model(None)
        self.data.set_default_sort_func(lambda *args: -1)
        self.data.set_sort_column_id(-1,
                                gtk.SORT_ASCENDING)

        try:
            for pos, entry in enumerate(src_list):
                self.data.append((
                    self.get_scaled_icon(entry.icon, ICON_SIZE),
                    entry.name,
                    xmlescape(entry.summarize()),
                    pos
                ))
        finally:
            self.data.set_sort_column_id(1,
                                gtk.SORT_ASCENDING)
            self.view.set_model(self.data)
            self.view.thaw_child_notify()

    def gtk_main_quit(self, widget, event):  # pylint: disable=R0201,W0613
        """Helper for Builder.connect_signals"""
        gtk.main_quit()

    def on_mi_rename_activate(self, _, pos):
        """Callback for the 'Rename...' context menu entry.

        (Because I don't want to force my Entrys to be GObject subclasses,
         so the model must be kept in sync manually.)
        """
        old_name = self.data[pos][1]

        field = gtk.Entry()
        field.set_text(old_name)

        dialog = gtk.Dialog("Rename %s" % old_name, self.mainwin,
                            gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        dialog.get_content_area().add(field)
        dialog.show_all()

        if dialog.run() == gtk.RESPONSE_ACCEPT:
            name = field.get_text()
            self.data[pos][1] = name
            self.entries[self.data[pos][3]].name = name
            # TODO: Persist
        dialog.destroy()

    def on_mi_hide_activate(self, _, pos):
        """Callback for the 'Hide' context menu entry.

        @todo: Implement this as more than a UX demo.
        """
        self.data.remove(self.data.get_iter(pos))

    def on_view_games_item_activated(self, _, path):
        """Handler to launch games on double-click"""
        cmd = self.entries[self.data[path][3]].default_launcher

        if cmd:
            cmd.run()
        # TODO: Add some sort of is-running notification to the GUI
        # TODO: Support screensaver suspension
        # TODO: Support runtime tracking (and, later, instrument with idleness
        #       detection) to track play time.
        # TODO: Write something which can save and restore ALL window positions
        # TODO: Hurry up and write that LD_PRELOAD hook to kill a game's
        #       ability to request fullscreen operation.

    # pylint: disable=no-self-use
    # def on_view_games_key_press_event(self, widget, event):
    #     """Handler for enabling the Delete key"""
    #     if (event.type == gtk.gdk.KEY_PRESS and
    #             event.keyval == gtk.keysyms.Delete):
    #         model, rows = widget.get_selection().get_selected_rows()
    #         rows = [gtk.TreeRowReference(model, x) for x in rows]
    #         for ref in rows:
    #             model.remove(model.get_iter(ref.get_path()))

    # pylint: disable=invalid-name
    def on_view_games_button_press_event(self, _, event=None):
        """Right-click and Menu button handler for the IconView.

        Source: http://faq.pygtk.org/index.py?req=show&file=faq13.017.htp
        """
        iconview = self.builder.get_object('view_games')
        if event and event.button == 3:  # Right Click
            evt_btn, evt_time = event.button, event.time
        elif event:                      # Non-right Click
            return None
        elif not event:                  # Menu key on the keyboard
            evt_btn, evt_time = None, None  # TODO: Make sure this works
            cursor = iconview.get_cursor()
            if cursor[0] is None:
                return None

        # Code to handle right-clicking on a non-selected entry
        # Source: http://www.daa.com.au/pipermail/pygtk/2005-June/010465.html
        path = iconview.get_path_at_pos(int(event.x), int(event.y))
        if not path:
            return True

        rows = iconview.get_selected_items()
        if not rows or path[0] != rows[0]:
            iconview.unselect_all()
            iconview.select_path(path[0])

        self.make_popup_for(path).popup(
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
