fuse-aexplorer
===============

A crude re-implementation of the Amiga Explorer protocol, for Linux/FUSE.

All knowledge of the protocol is either based on Mark Street's lxamiga or
[lxamiga.pl](https://github.com/marksmanuk/lxamiga) or gained by
monitoring communication between the original Windows version of
Amiga Explorer and the Amiga side.

This software is highly experimental and use is fully AT YOUR OWN RISK.
Please don't blame me or Cloanto or anyone if anything breaks.

If you experience any issues (and that's almost guaranteed), please use
[Cloanto's official Windows software](https://www.amigaforever.com/ae/)
instead. It's a great, stable software package.


Usage:
-------

./fuse-aexplorer /mnt/amiga /dev/ttyUSB0 19200

cp -a myfile "/mnt/amiga/RAM\:Ram\ Disk/"




DATA LOSS WARNING
==================

Comments and attributes without an equivalence in Linux are lost
whenever a write operation (including changing attributes) is
performed on a file.

I'm sure there's more, but I've forgotten about it.



Things that are broken
=======================

A lot. The Amiga Explorer protocol really isn't meant to be used as
a "network file system".

Examples:

 - Reading only a part of a file isn't possible.
   There is a hack to only read the start of it, thus making Thunar
   and other GIO programs not get stuck completely.

 - Changing a part of a file or appending data isn't possible - it
   has to be rewritten from scratch.
   We're buffering a file and send it when flush() is called.

 - Setting a file's modification date can only be done when
   writing it from scratch.
   Use 'cp -a' to copy your files.

 - Files and folders being deleted on the Amiga while we know that they
   exist (i.e. their attributes are cached) causes undefined behavior.

 - And many more hacks!
   Really, go use the original software instead!



TODO
=====

Search the code for TODO and NOTE.

:-)



Thanks
=======

Cloanto for Amiga Explorer. Great stuff and a life saver.

Mark Street for lxamiga and
[lxamiga.pl](https://github.com/marksmanuk/lxamiga) - this gave me a
head start in understanding the protocol.



License
========

GNU General Public License v2 only.
