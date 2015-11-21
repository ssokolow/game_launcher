#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""""""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__version__ = '0.0pre0'

import itertools, logging, os, zipfile
log = logging.getLogger(__name__)

# IMPORTANT: Headers override extensions but ordering still encodes precedence.
# (If a type has a header definition, its extensions are only used to inform
# the filter_names() function)
# TODO: Need support for subtests (eg. for EXE)
filetypes = [
    # TODO: https://en.wikipedia.org/wiki/Executable_and_Linkable_Format
    # TODO: Decide what to do with the execute bits, if anything
    (b'\x7fELF', ['.x86', '.x86_64', '.bin'], 'TODO: Identify ELF target'),
    (b'#!', ['.sh', '.py', '.pl', '.rb'], 'UNIX Script'),
    # TODO: http://www.delphidabbler.com/articles?article=8
    (b'MZ', ['.exe'], 'TODO: Identify EXE Type'),
    # http://www.delorie.com/djgpp/doc/coff/filhdr.html
    # http://wiki.osdev.org/COFF
    (b'\x4c\x01', ['.exe'], 'Bare i386 COFF (DJGPP?)'),
    (b'\x4c\0\0\0', ['.lnk'], "Windows Shortcut"),
    # TODO: Need a test file for uncompressed Flash
    (b'FWS', ['.swf'], 'Adobe Flash'),
    (b'CWS', ['.swf'], 'Adobe Flash (zlib-compressed)'),
    (lambda fobj, ext: zipfile.is_zipfile(fobj) and ext == '.jar',
        ['.jar'], "Java JAR archive"),
    # TODO: Decide how to support header matches for .desktop files using a
    #       a regex something like this such that it helps rather than hurts:
    #       re.compile(r"\s*|^#[^\n]*\n)+\[Desktop Entry\]")
    (None, ['.desktop'], "XDG Desktop Entry"),
    # TODO: Decide how to make the .bat/.cmd detection more stringent
    #       At the very least, do an advisory check with a regex like this:
    #         re.compile(r"\s*(rem|set|@?echo off)", re.I)
    (None, ['.bat'], "DOS Batch file"),
    # Note: .btm isn't recognized because no game would use it for the launcher
    (None, ['.cmd'], "OS/2 or Windows NT batch file"),
    (None, ['.com'], "COM binary"),
    # http://www.smsoft.ru/en/pifdoc.htm
    # TODO: Verify that the file begins with a null byte but don't let a null
    #       byte be interpreted as proof of a PIF file
    # TODO: Subtype based on length, then check headers at 0x171 and beyond
    (None, ['.pif'], "PIF file"),
]

# NOTE: For a stricter mode or pass, I need to do the following:
# - Verify that ELF files are for a compatible arch and platform
# - Verify that UNIX script shebangs point to valid interpreters
#   and do a basic interpreter<->extension matching sanity check.
# - Identify the subtype of EXE file in the greatest detail possible
# - Check that LNK files have valid, local targets
# - Verify that JARs have manifests which point to existing entry point classes
# - Parse .desktop files and check whether they point to a usable target
# - Look up how libmagic identifies probable .COM files
# - Parse .PIF files and check whether they point to a usable target

def filter_names(paths):
    """Helper for identifying candidates when it's not feasible to inspect
    the headers on every single file in a partition.
    """
    exts = list(itertools.chain.from_iterable(x[1] for x in filetypes))
    return [x for x in paths if os.path.splitext(x)[1].lower() in exts]
    # TODO: Also support inferring the notability of "foo" from the existence
    #       of "foo.x86" and/or "foo.x86_64"
    # TODO: When stat() is considered an acceptable burden, the execute bits
    #       can be a useful cue after applying util.executable.NON_BINARY_EXTS

# TODO: The whole point of this is to be more specific than the mimetypes
# returned by libmagic's machine-readable mode, so design a proper return API
# for it.
def identify_file(path):
    # Magic numbers have precedence
    with open(path, 'rb') as fobj:
        magic, ext = fobj.read(4), os.path.splitext(path)[1].lower()
        for magic_pat, _, result in filetypes:
            if magic_pat:
                if (isinstance(magic_pat, basestring) and
                        magic.startswith(magic_pat)):
                    return result
                elif callable(magic_pat) and magic_pat(fobj, ext):
                    return result
    # ...and then extension checks for things with none like .BAT
    for magic_pat, exts, result in filetypes:
        if magic_pat:
            # If it didn't match the header, don't let the extension pull it
            # back into consideration.
            # TODO: Write unit tests which verify this behaviour
            #       (eg. text_file.exe shouldn't match EXE)
            continue
        for ext_pat in exts:
            if ext == ext_pat:
                return 'Possibly %s' % result
    return "Not a recognized executable"

def main():
    """The main entry point, compatible with setuptools entry points."""
    from argparse import ArgumentParser
    parser = ArgumentParser(usage="%(prog)s [options] <argument> ...",
            description=__doc__.replace('\r\n', '\n').split('\n--snip--\n')[0])
    parser.add_argument('--version', action='version',
            version="%%(prog)s v%s" % __version__)
    parser.add_argument('-v', '--verbose', action="count", dest="verbose",
        default=2, help="Increase the verbosity. Use twice for extra effect")
    parser.add_argument('-q', '--quiet', action="count", dest="quiet",
        default=0, help="Decrease the verbosity. Use twice for extra effect")
    parser.add_argument('files', nargs='+', help="Files to identify")
    # Reminder: %(default)s can be used in help strings.

    args = parser.parse_args()

    # Set up clean logging to stderr
    log_levels = [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose - args.quiet, len(log_levels) - 1)
    args.verbose = max(args.verbose, 0)
    logging.basicConfig(level=log_levels[args.verbose],
                        format='%(levelname)s: %(message)s')

    interesting_names = filter_names(args.files)
    skipped = []
    for path in args.files:
        if path in interesting_names:
            print("%s: %s" % (identify_file(path), path))
        else:
            skipped.append(path)

    print("\nSkipped:\n\t%s" % '\n\t'.join(skipped))

if __name__ == '__main__':
    main()

# vim: set sw=4 sts=4 expandtab :
