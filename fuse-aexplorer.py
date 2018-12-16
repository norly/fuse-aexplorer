#!/usr/bin/env python
#
# A FUSE filesystem to access an Amiga's files via Cloanto's Amiga Explorer.
#
# Known limitations:
#  See README.
#
# SPDX-License-Identifier: GPL-2.0
#


from fusepy import FUSE
import sys

from AEpy.AELink import AELinkSerial
from AEpy.AESession import AESession
from AEpy.AEFuse import AEFuse
from AEpy import FusePatches





if __name__ == '__main__':
    # Monkey patch fusepy
    FusePatches.patch_max_readahead(512)

    serspeed = 19200

    if len(sys.argv) - 1 < 2:
        print('Only ' + str(len(sys.argv) - 1) + ' arguments given.')
        print('Usage: ' + sys.argv[0] + ' <mount point> <serial device> [serial speed]')

        sys.exit(-1)

    if len(sys.argv) - 1 > 2:
        serspeed = int(sys.argv[3])

    link = AELinkSerial(sys.argv[2], serspeed)
    session = AESession(link)
    fuse = AEFuse(session)
    FUSE(fuse, sys.argv[1], nothreads=True, foreground=True)
