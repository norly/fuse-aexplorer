# Ugly patches for fusepy to accommodate inflexible userspace applications.
#

from ctypes import c_uint, cast, POINTER, Structure
from fusepy import FUSE


class fuse_conn_info(Structure):
    _fields_ = [
        ('proto_major', c_uint),
        ('proto_minor', c_uint),
        ('async_read', c_uint),
        ('max_write', c_uint),
        ('max_readahead', c_uint),
        ('capable', c_uint),
        ('want', c_uint),
        ('max_background', c_uint),
        ('congestion_threshold', c_uint)
    ]


# Ugly patch for fusepy to allow changing max_readahead.
#
# This is necessary for FUSE filesystems which need to avoid unnecessary
# data transfers.
#
# Example:
# If a GIO (as in GLib/GNOME's GIO) based file manager (e.g. XFCE's Thunar)
# tries to determine each file's type by inspecting its header (GLib 2.50
# reads up to 4 KB of each file), this results in a lot of traffic. If the
# kernel increases this to 16 KB as part of its buffered I/O's readahead,
# things become very slow on exotically slow links or host media.
# In fact, this patch has been written with a 2 KByte/s link in mind.
#
# Why not turn off this header-sniffing feature in userspace?
# Because... Neither Thunar nor GLib/GIO have this option, and exotic FUSE
# filesystems still need to work on them until they have a mechanism to turn
# this off. Preferably with a hint in stat() or statfs().
#
# NOTE:
# The kernel will impose a lower bound on max_readahead.
# As of 4.9 on x86-64, this is 4096 bytes.
# (still a lot on a 2 KB/s link, but Thunar won't be *completely* useless)
#
def patch_max_readahead(max_readahead):
    old_init = FUSE.init

    def _new_fuse_init(self, conn):
        conn2 = cast(conn, POINTER(fuse_conn_info))
        conn2.contents.max_readahead = max_readahead
        return old_init(self, conn)

    FUSE.init = _new_fuse_init
