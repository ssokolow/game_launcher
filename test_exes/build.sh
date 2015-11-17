#!/bin/bash
# In its current form, this code expects the following tools to be present:
#
# (Though it won't fail if some are missing. If you just want convenience,
#  set up OpenWatcom since it generates the majority of the test files and
#  one of each format under test)
#
# DOSEmu DOS Emulator
#   Just install the dosemu package in the Debian/Ubuntu repositories
#
# DJGPP cross-compiler
#   Obtain from: https://github.com/andrewwutw/build-djgpp
#   Install to:  ~/opt/djgpp/
#
# MinGW-W64 cross-compiler
#   Just install the mingw-w64 package in the Debian/Ubuntu repositories
#
# Mono C# compiler
#   Just install the mono-dev package in the Debian/Ubuntu repositories
#
# Pacific C
#   Obtain from: http://www.freedos.org/software/?prog=pacific-c
#   Installation:
#    1. Run `dosemu` and then type `exitemu` in the resulting window
#    2. Install Pacific C to ~/.dosemu/drive_c/
#
# OpenWatcom cross-compiler
#   Obtain from: https://github.com/open-watcom/open-watcom-v2
#   Installation:
#    1. Download the binary build for Linux
#    2. mkdir -p ~/opt/openwatcom
#    3. cd ~/opt/openwatcom
#    4. unzip path/to/openwatcom/installer
#    5. cd binl
#    6. file * | grep ELF | cut -d: -f1 | xargs chmod +x
#
#   (On my system, attempting to run the installer causes it to crash)
#
# UPX executable packer
#   Just install the upx-ucl package in the Debian/Ubuntu repositories
#

SRC_FILE="hello.c"
DOSEMU_DRIVE=~/.dosemu/drive_c
DJGPP_ROOT=~/opt/djgpp
GCC_COMMON_ARGS="-Wall -pedantic $SRC_FILE"
PACC="c:\\pacific\\bin\\pacc.exe"
WATCOM=~/opt/openwatcom

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

    case "$1" in  # Workaround for broken 16-bit support in owcc
        com)
            # shellcheck disable=SC2086
            wcl -q -bcl="$1" "$SRC_FILE" -fe="hello_owatcom16.com" $3 ;;
        dos|os2|windows)
            # shellcheck disable=SC2086
            wcl -q -bcl="$1" "$SRC_FILE" -fe="hello_owatcom16_$1.exe" $3 ;;
        win386)
            # Resources used:
            # http://www.os2museum.com/wp/watcom-win386/
            # http://openwatcom.contributors.narkive.com/dAgYeOP9/win386-question-for-tutorial
            outfile="hello_owatcom_$1"
            # shellcheck disable=SC2086
            wcl386 -q -bt=windows -l=win386 "$SRC_FILE" -fe="$outfile".rex $3
            # TODO: Figure out how to stop wbind from segfaulting on success
            wbind "$outfile".exe -nq -s "$WATCOM/binw/win386.ext"
            rm "$outfile".rex ;;
        *)
            # shellcheck disable=SC2086
            owcc -b"$1" "$SRC_FILE" -o "hello_owatcom_$1.exe" $3 ;;
    esac
    rm hello.o
}

upx_pack() {
    # shellcheck disable=SC2086
    upx -qq "$1" -o"${1%.*}.upx$2.${1##*.}" $3
}

echo " * Compiling for DOS with Pacific C (Real Mode)"
dosemu_build "$PACC -Q -W9" hello_pacific.exe

echo " * Compiling for DOS with DJGPP (Protected Mode)"; (
    export PATH="$DJGPP_ROOT/bin/:$PATH"
    # shellcheck disable=SC2086
    i586-pc-msdosdjgpp-gcc $GCC_COMMON_ARGS -o hello_djgpp.exe
)

# TODO:
# - Look for a way to generate the i386-dos32.tmt.adam format UPX supports
#   - Only non-UPX mention I've found so far:
#     http://board.flatassembler.net/topic.php?p=179760
# - Determine whether any of these generate usefully different EXE files
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