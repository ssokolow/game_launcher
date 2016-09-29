"""Code to provide cached, scaled icons on demand"""

__author__ = "Stephan Sokolow (deitarion/SSokolow)"
__license__ = "GNU GPL 3.0 or later"

# pylint: disable=multiple-imports
import os, operator

# pylint: disable=no-name-in-module
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon

from xdg.IconTheme import getIconPath

def size_maxed(inner, outer, exact=False):
    """Return True if the inner QSize meets or exceeds the outer QSize in at
    least one dimension.

    If exact is True, return False if inner is larger than outer in at least
    one dimension."""
    oper = operator.eq if exact else operator.ge

    return (oper(inner.width(), outer.width()) or
            oper(inner.height(), outer.height()))

class IconProvider(object):
    """Qt model class to adapt game-handling backend to Qt Views"""
    def __init__(self, fallback_name):
        self.icon_cache = {}  # TODO: Do this properly
        self.fallback_name = fallback_name

    @staticmethod
    def ensure_icon_size(icon, desired):
        """Workaround to QIcon not offering an upscale to match' mode

        This implements the "smoothed nearest" upscaling algorithm that I've
        found to be the best compromise for naively upscaling small icons
        of varying aesthetics.
        """
        if not icon:
            return

        if isinstance(desired, int):
            desired = QSize(desired, desired)

        # TODO: Use availableSizes() and pick the closest size, regardless of
        #       whether it's larger or smaller.
        #       (I'll also want to cache the source images separately from the
        #        calculated ones so errors don't compound)
        offered = icon.actualSize(desired)

        # If the desired size is already available, just return it
        # TODO: Check whether oversized icons look better when we downscale
        #       them here rather than letting the QPainter do it.
        if size_maxed(offered, desired):
            return icon

        pixmap = icon.pixmap(desired)

        # Use nearest-neighbour rescaling to get to the closest smaller integer
        # multiple before letting smooth scaling take over
        # TODO: Does floor division or rounding produce better-looking output?
        scale_factor = min(desired.width() // offered.width(),
                           desired.height() // offered.height())
        if size_maxed(offered * scale_factor, desired):
            scale_factor -= 1
        if scale_factor > 1:
            pixmap = pixmap.scaled(offered * scale_factor,
                Qt.KeepAspectRatio, Qt.FastTransformation)

        # Then use smooth scaling to take the last step
        pixmap = pixmap.scaled(desired,
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.addPixmap(pixmap)

        # Hack around fromTheme producing a QIcon which ignores addPixmap
        # TODO: Add a slot which GamesView can connect to in order to
        #       specify a list of desired sizes, so we don't need to load
        #       all of them.
        if icon and icon.actualSize(desired) != desired:
            old_icon = icon
            icon = QIcon(pixmap)
            for size in old_icon.availableSizes():
                icon.addPixmap(old_icon.pixmap(size))

        return icon

    @staticmethod
    def lookup_local(name):
        if name:
            path_base = os.path.join(os.path.dirname(__file__), name)
            for ext in ('svgz', 'svg', 'png'):
                icon_path = '{}.{}'.format(path_base, ext)
                if os.path.exists(icon_path):
                    icon = QIcon(os.path.join(icon_path))
                    if not icon.isNull():
                        return icon
        return None

    # TODO: Do this properly
    def get_icon(self, icon_name, icon_size):
        """Workaround for Qt not implementing a fallback chain in fromTheme"""
        # Always let the cache service requests first
        if icon_name in self.icon_cache:
            return self.icon_cache[icon_name]

        # Skip right to the fallback if it's None or an empty string
        if icon_name:
            # Give Qt the opportunity to make a fool out of itself
            if os.path.isfile(icon_name):
                icon = QIcon(icon_name)
            else:
                icon = QIcon.fromTheme(icon_name)

            # Resort to PyXDG to walk the fallback chain properly
            # TODO: Better resolution handling
            if not icon or icon.isNull():
                icon = QIcon(getIconPath(icon_name, icon_size,
                                         theme=QIcon.themeName()))
        else:
            icon = None

        if not icon or icon.isNull():
            icon = self.lookup_local(icon_name)

        # If we still couldn't get a result, retrieve the fallback icon in a
        # way which will allow a cache entry here without duplication
        if not icon or icon.isNull() and icon_name != self.fallback_name:
            icon = self.get_icon(self.fallback_name, icon_size)

        # Populate the cache
        icon = self.ensure_icon_size(icon, icon_size)
        self.icon_cache[icon_name] = icon
        return icon
