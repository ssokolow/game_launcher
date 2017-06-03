#!/bin/bash
# In its current form, this code expects the following tools to be present:
#
# (Though it won't fail if some are missing. If you just want convenience,
#  set up OpenWatcom since it generates the majority of the test files and
#  one of almost every format under test)
#
#
# The following packages:
#   build-essential
#   dosemu
#   haxe
#   mingw-w64
#   mono-dev
#   openjdk-7-jdk (or another provider of javac)
#   upx-ucl
#
# Dev86 cross-compiler
#   Obtain from: http://v3.sk/~lkundrak/dev86/
#     (Must compile from source or bcc-cpp will be missing)
#   Install to ~/opt/dev86 OR set $DEV86_ROOT OR install in $PATH
#
# DJGPP cross-compiler
#   Obtain from: https://github.com/andrewwutw/build-djgpp
#   Install to ~/opt/djgpp/ OR set $DJGPP_ROOT OR install in $PATH
#
# OpenWatcom cross-compiler
#   Obtain from: https://github.com/open-watcom/open-watcom-v2
#   Installation:
#    1. Download a binary build for Linux
#    2. mkdir -p ~/opt/openwatcom
#    3. unzip path/to/openwatcom/installer -d ~/opt/openwatcom
#       (On my system, attempting to run the installer causes it to crash)
#    4. file ~/opt/openwatcom/binl/* | grep ELF | cut -d: -f1 | xargs chmod +x
#
# Pacific C (because /usr/bin/file sees its output as different from others)
#   Obtain from: http://www.freedos.org/software/?prog=pacific-c
#   Installation:
#    1. Run `dosemu` and then type `exitemu` in the resulting window
#    2. Unzip Pacific C such that C:\pacific\bin\pacc.exe exists
#       (If not using pacificx.zip, unzip pacific.exe and add pacc.exe)
#
# PyLNK (optional)
#   Used to build a known clean .lnk file for test purposes
#   If you want to rebuild rather than using the included .lnk file, run:
#     sudo pip install pylnk
#
# You may override the following variables outside this script and they will
# be obeyed:
#   DEV86_ROOT    Path to the --prefix where Dev86 was installed
#   DOSEMU_DRIVE  Path to the folder DOSEmu will mount as C:
#   DJGPP_ROOT    Path to your DJGPP cross-compiler root folder
#   PACC          DOS-format path to Pacific C from within DOSEmu
#   WATCOM        Path to your Open Watcom installation

DEV86_ROOT="${DEV86_ROOT:-$HOME/opt/dev86}"
DOSEMU_DRIVE="${DOSEMU_DRIVE:-$HOME/.dosemu/drive_c}"
DJGPP_ROOT="${DJGPP_ROOT:-$HOME/opt/djgpp}"
PACC="${PACC:-c:\\pacific\\bin\\pacc.exe}"
WATCOM="${WATCOM:-$HOME/opt/openwatcom}"

SRC_FILE="hello.c"
GCC_COMMON_ARGS="-Wall -Wextra -pedantic $SRC_FILE"

cd "$(dirname "$0")"
rm -f ./*.o ./*.exe ./*.com ./*.class ./*.jar ./hello_gcc.* ./*.swf

dosemu_build() {
    cp "$SRC_FILE" "$DOSEMU_DRIVE"
    dosemu -dumb "$1 $3 -OC:\\out.exe C:\\$SRC_FILE"
    mv "$DOSEMU_DRIVE/out.exe" "$2"
    rm "$DOSEMU_DRIVE/$SRC_FILE"
}

mono_build() {
    echo " * Compiling hello.cs as $1 on $2 with Mono"
    mcs -out:"hello_csharp_$1_$2.exe" "-target:$1" "-platform:$2" hello.cs
}

# References used:
#  https://wiki.archlinux.org/index.php/Open_Watcom
#  http://sourceforge.net/p/openwatcom/tickets/5/
#  http://openwatcom.contributors.narkive.com/UWRMUzGK/building-ne-executables
openwatcom_build() {
    echo " * Compiling for $1 with OpenWatcom"
    export WATCOM
    export PATH="$WATCOM/binl:$PATH"
    export EDPATH="$WATCOM/eddat"
    export WIPFC="$WATCOM/wipfc"
    export INCLUDE="$2"

    # Minimal duplication in naming
    outname="hello_owatcom_$1"
    case "$1" in
        com) outfile="$outname".com ;;
        *)   outfile="$outname".exe ;;
    esac

    # Workaround for broken 16-bit support in released owcc
    case "$1" in
        com|dos|os2|windows) wcl -w4 -q -bcl="$1" "$SRC_FILE" -fe="$outfile" ;;
        *) owcc -Wall -b"$1" "$SRC_FILE" -o "$outfile" ;;
    esac
    rm hello.o

    # Support Win386
    # Resources used:
    # http://www.os2museum.com/wp/watcom-win386/
    # http://openwatcom.contributors.narkive.com/dAgYeOP9/win386-question-for-tutorial
    if [ "$1" = "win386" ]; then
        mv "$outfile" "tmp_w386".rex
        wbind "tmp_w386.exe" -nq
        mv "tmp_w386.exe" "$outfile"
        rm tmp_w386.rex
    fi
}

upx_pack() {
    # shellcheck disable=SC2086
    upx -qq "$1" -o"${1%.*}.upx$2.${1##*.}" $3
}

echo "----------------------------------"
echo " Compiling test files from source "
echo "----------------------------------"

echo " * Compiling for DOS with Dev86 (Real Mode)"; (
    # shellcheck disable=SC2030,2031
    export PATH="$PATH:$DEV86_ROOT/bin/"
    bcc -Md hello_dev86.c -o hello_dev86.com
)

echo " * Compiling for DOS with Pacific C (Real Mode)"
dosemu_build "$PACC -Q -W9" hello_pacific.exe

echo " * Compiling for DOS with DJGPP (Protected Mode)"; (
    # shellcheck disable=SC2031
    export PATH="$PATH:$DJGPP_ROOT/bin/"
    # shellcheck disable=SC2086
    i586-pc-msdosdjgpp-gcc $GCC_COMMON_ARGS -o hello_djgpp.exe
)

# TODO:
# - Look for a way to generate the "rtm32/pe" variant of PE from `man upx`.
#   Apparently, it's used by the Borland Turbo C/Pascal DOS extenders:
#   - http://www.vogons.org/viewtopic.php?t=25997
# - Find a copy of TMT Pascal Lite for DOS version 3.90d so I can generate
#   the i386-dos32.tmt.adam format mentioned in `man upx`:
#   - http://wiki.freepascal.org/Hello%2C_World
#   - http://www.edm2.com/index.php/TMT_Pascal
#   - http://www.frameworkpascal.com/download.htm
#   - http://pascal.sources.ru/tmt/download.htm
#   - Possibly related:
#     http://board.flatassembler.net/topic.php?p=179760
#   - "Hello, world!
#
#      This program was compiled with TMT Pascal Lite for DOS
#      for the purpose of testing code which detects or manipulates
#      the i386-dos32.tmt.adam file format.
#
#      In accordance with the terms of the TMT Pascal Lite license agreement,
#      you may not charge money for this binary."
#   - For compressed Win31 and OS/2 test EXEs, use a new enough OpenWatcom, and
#     LxLite in forced mode. hello.c shouldn't trip any of the remaining
#     incompatibilities.
#     - http://www.edm2.com/index.php/LxLite
# - Determine whether any of these generate usefully different EXE files
#   - http://freedos.sourceforge.net/software/?prog=cc386
#   - http://ladsoft.tripod.com/orange_c_compiler.html
#   - http://www.desmet-c.com/
#     + the various assemblers in the FreeDOS library
#   - http://www.t3x.org/subc/
#   - http://www.freepascal.org/ (Win32, Win64, GO32v2, and i8086 targets)
#   - http://www.program-transformation.org/Transform/PcExeFormat
#   - https://github.com/madebits/msnet-netz-compressor
#   - gzexe for ELF
#   - UPX's -8086 compression mode for DOS targets
#   - LxLite-compressed DOS/Win31 programs instead of UPX-compressed
#   - http://www.compression.dk/cmview/View?id=10005
# - Decide whether there's enough PlayStation homebrew to justify generating
#   a PlayStation test EXE plus associated UPX-compressed version.
# - Is there anything useful I can learn from this tool?
#   http://unp.bencastricum.nl/

# References used:
#  ftp://ftp.openwatcom.org/pub/manuals/current/lguide.pdf#page=15
#  https://wiki.archlinux.org/index.php/Open_Watcom
openwatcom_build com "$WATCOM/h"
openwatcom_build dos "$WATCOM/h"
openwatcom_build dos4g "$WATCOM/h"
openwatcom_build dos4gnz "$WATCOM/h"
openwatcom_build os2 "$WATCOM/h:$WATCOM/h/os21x"
openwatcom_build os2v2 "$WATCOM/h:$WATCOM/h/os2"
openwatcom_build windows "$WATCOM/h:$WATCOM/h/win"
openwatcom_build win386 "$WATCOM/h:$WATCOM/h/win"
openwatcom_build win95 "$WATCOM/h:$WATCOM/h/win"
openwatcom_build nt "$WATCOM/h:$WATCOM/h/nt"

echo " * Compiling for Win32 with MinGW"
# shellcheck disable=SC2086
i686-w64-mingw32-gcc $GCC_COMMON_ARGS -o hello_mingw32.exe

echo " * Compiling for Win64 with MinGW"
# shellcheck disable=SC2086
x86_64-w64-mingw32-c++ $GCC_COMMON_ARGS -o hello_mingw64.exe

for platform in x86 x64 itanium arm; do
    mono_build exe "$platform"
    # TODO: Figure out whether the Console/GUI distinction is relevant
    #       and, if so, generate more variations from OpenWatcom and MinGW
    #mono_build winexe x86
done

echo " * Attempting to rebuild test .lnk file"
python2 - << EOF
import pylnk, os

# If we got this far, PyLNK is installed
if os.path.exists('hello.lnk'):
    os.remove('hello.lnk')

lnk_file = pylnk.Lnk()
lnk_file.specify_local_location('C:\\\\')
with open('hello.lnk', 'wb') as fobj:
    lnk_file.save(fobj)
EOF

echo " * Building test JAR file"
javac hello.java
jar cfe hello.jar hello hello.class
echo " * Building test .pack.gz from JAR file"
pack200 hello.pack.gz hello.jar
rm hello.class

echo " * Building test SWF file (compressed)"
haxe -main Hello -swf hello_c.swf

echo " * Compiling native ELF64 binary with GCC for comparison"
# shellcheck disable=SC2086
gcc $GCC_COMMON_ARGS -ohello_gcc.x86_64
echo " * Compiling native ELF32 binary with GCC for comparison"
# shellcheck disable=SC2086
gcc $GCC_COMMON_ARGS -m32 -ohello_gcc.x86

# TODO: Make this work
# - https://stackoverflow.com/questions/8303536/generating-a-out-file-format-with-gcc
# - https://groups.google.com/forum/#!topic/comp.os.linux.development.system/uIrJI1wNdOs
echo " * Compiling native 32-bit a.out binary with GCC for comparison"
# shellcheck disable=SC2086
gcc -Wl,--oformat=a.out-i386-linux -static-libgcc $GCC_COMMON_ARGS -m32 -ohello_gcc.aout

# TODO: Adjust ELF GCC output to avoid NotCompressibleException
echo ""
echo "----------------------------------"
echo " Generating UPX-compressed copies "
echo "----------------------------------"
for X in *.exe *.com hello_gcc.*; do
    upx_pack "$X"
done
upx_pack hello_djgpp.exe .coff --coff

# TODO: Decide which stubs to bind this to
#upx_pack hello_owatcom_dos4g.exe .le --le

echo
echo "====================================="
echo

echo " * Removing unnecessary execute bits "
chmod -x ./*.exe ./*.com

echo
echo "Done."
