#!/bin/bash
# In its current form, this code expects the following tools to be present:
#
# (Though it won't fail if some are missing. If you just want convenience,
#  set up OpenWatcom since it generates the majority of the test files and
#  one of each format under test)
#
# The following packages:
#   dosemu
#   mingw-w64
#   mono-dev
#   upx-ucl
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
# Pacific C
#   Obtain from: http://www.freedos.org/software/?prog=pacific-c
#   Installation:
#    1. Run `dosemu` and then type `exitemu` in the resulting window
#    2. Unzip Pacific C such that C:\pacific\bin\pacc.exe exists
#       (If not using pacificx.zip, unzip pacific.exe and add pacc.exe)
#
# You may override the following variables outside this script and they will
# be obeyed:
#   DOSEMU_DRIVE  Path to the folder DOSEmu will mount as C:
#   DJGPP_ROOT    Path to your DJGPP cross-compiler root folder
#   PACC          DOS-format path to Pacific C from within DOSEmu
#   WATCOM        Path to your Open Watcom installation

DOSEMU_DRIVE="${DOSEMU_DRIVE:-$HOME/.dosemu/drive_c}"
DJGPP_ROOT="${DJGPP_ROOT:-$HOME/opt/djgpp}"
PACC="${PACC:-c:\\pacific\\bin\\pacc.exe}"
WATCOM="${WATCOM:-$HOME/opt/openwatcom}"

SRC_FILE="hello.c"
GCC_COMMON_ARGS="-Wall -pedantic $SRC_FILE"

cd "$(dirname "$0")"
rm -f ./*.exe ./*.com

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
    # TODO: Figure out how to stop wbind from segfaulting on success
    if [ "$1" = "win386" ]; then
        mv "$outfile" "$outname".rex
        wbind "$outfile" -nq -s "$WATCOM/binw/win386.ext"
        rm "$outname".rex
    fi
}

upx_pack() {
    # shellcheck disable=SC2086
    upx -qq "$1" -o"${1%.*}.upx$2.${1##*.}" $3
}

echo " * Compiling for DOS with Pacific C (Real Mode)"
dosemu_build "$PACC -Q -W9" hello_pacific.exe

echo " * Compiling for DOS with DJGPP (Protected Mode)"; (
    export PATH="$PATH:$DJGPP_ROOT/bin/"
    # shellcheck disable=SC2086
    i586-pc-msdosdjgpp-gcc $GCC_COMMON_ARGS -o hello_djgpp.exe
)

# TODO:
# - Look for a way to generate the i386-dos32.tmt.adam format UPX supports
#   - Only non-UPX mention I've found so far:
#     http://board.flatassembler.net/topic.php?p=179760
# - Determine whether any of these generate usefully different EXE files
#   - http://v3.sk/~lkundrak/dev86/
#   - http://freedos.sourceforge.net/software/?prog=cc386
#   - http://ladsoft.tripod.com/orange_c_compiler.html
#   - http://www.desmet-c.com/
#   - https://github.com/alexfru/SmallerC
#     + the various assemblers in the FreeDOS library
#   - http://www.t3x.org/subc/

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

echo " * Generating UPX-compressed copies"
for X in *.exe *.com; do
    upx_pack "$X"
done
upx_pack hello_owatcom_dos4g.exe .le --le
upx_pack hello_djgpp.exe .coff --coff

echo " * Removing unnecessary execute bits"
chmod -x ./*.exe ./*.com
