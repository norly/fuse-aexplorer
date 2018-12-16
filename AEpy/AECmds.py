import binascii
import serial
from stat import S_IRUSR, S_IWUSR, S_IXUSR, S_IRGRP, S_IXGRP, S_IROTH, S_IXOTH, S_IFDIR, S_IFREG
import struct

from AESession import AESession
import AEMultipart


###################################
#
# All paths are without leading /
# All paths are in Amiga charset.
#
###################################


# Command 0x01
# Cancel a running operation.
#
def cancel(session):
    session.sendMsg(1, b'')



# Command 0x64
# List a directory.
#
def dir_list(session, path):
    print("AECmds.dir_list: " + path)

    session.sendMsg(0x64, path + b'\x00\x01')

    dirlist = AEMultipart.recv(session)
    # TODO: Check for None returned, meaning that the path doesn't exist.
    #       Actually, what can we return then?
    #       None is not iterable, and [] indicates an empty directory.
    close(session)


    # Parse dirlist

    (numents,) = struct.unpack('!L', dirlist[0:4])
    dirlist = dirlist[4:]

    kids = {}
    #kids['.'] = (dict(st_mode=(S_IFDIR | 0o755), st_nlink=2), {})
    #kids['..'] = (dict(st_mode=(S_IFDIR | 0o755), st_nlink=2), {})

    while numents > 0:
        assert len(dirlist) > 29
        (entlen, size, used, type, attrs, mdays, mmins, mticks, type2)  = struct.unpack('!LLLHHLLLB', dirlist[0:29])
        # entlen  - Size of this entry in the list, in bytes
        # size    - Size of file.
        #           For drives, total space.
        # used    - 0 for files and folders.
        #           For drives, space used.
        # type    - ?
        # attrs   - Amiga attributes
        # mdays   - Last modification in days since 1978-01-01
        # mmins   - Last modification in minutes since mdays
        # mticks  - Last modification in ticks (1/50 sec) since mmins
        # type2   - 0: Volume
        #         - 1: Volume
        #         - 2: Directory
        #         - 3: File
        #         - 4: ROM
        #         - 5: ADF
        #         - 6: HDF
        assert entlen <= len(dirlist)

        name = dirlist[29:entlen].split(b'\x00')[0].decode(encoding="iso8859-1")

        dirlist = dirlist[entlen:]
        numents -= 1

        st = {}
        st = {}
        st['st_mode'] = 0
        #if attrs & 0x40: st['st_mode'] |= Script
        #if attrs & 0x20: st['st_mode'] |= Pure
        #if attrs & 0x10: st['st_mode'] |= Archive
        if not attrs & 0x08: st['st_mode'] |= S_IRUSR | S_IRGRP | S_IROTH # Read
        if not attrs & 0x04: st['st_mode'] |= S_IWUSR # Write
        if not attrs & 0x02: st['st_mode'] |= S_IXUSR | S_IXGRP | S_IXOTH # Execute
        #if not attrs & 0x01: st['st_mode'] |=  Delete

        # Check for directory
        if type & 0x8000:
            st['st_mode'] |= S_IFDIR
        else:
            st['st_mode'] |= S_IFREG
            st['st_nlink'] = 1

        st['st_size'] = size

        st['st_mtime']  = (2922*24*60*60)   # Amiga epoch starts 1978-01-01
        st['st_mtime'] += (mdays*24*60*60)  # Days since 1978-01-01
        st['st_mtime'] += (mmins*60)        # Minutes
        st['st_mtime'] += (mticks/50)       # Ticks of 1/50 sec

        st['st_blksize'] = session.packetsize - 4

        # TODO: Convert time zone.
        # Amiga time seems to be local time, we currently treat it as UTC.

        kids[name] = (st, None)

    return kids



# Command 0x65
# Read a file.
#
def file_read_start(session, path):
    print("AECmds.file_read_start: " + path)

    # Request file
    session.sendMsg(0x65, path + b'\x00')

    # Get file response header
    (filelen, pktsize) = AEMultipart.recvHeader(session)

    # TODO: Check for None returned, meaning that the path doesn't exist.
    # This may not be necessary in case FUSE always issues a getattr()
    # beforehand.

    return filelen


def file_read_next(session):
    (blockOffset, blockData) = AEMultipart.recvBlock(session)

    if (blockData == None):
        blen = None
    else:
        blen = len(blockData)

    print("AECmds.file_read_next: " + str(blen) + ' @ ' + str(blockOffset))

    return (blockOffset, blockData)



# Command 0x66
# Write a complete file and set its attributes and time.
#
def file_write(session, path, amigaattrs, unixtime, filebody):
    print('AECmds.file_write: ' + path + ' -- ' + str(len(filebody)))

    filelen = len(filebody)

    _utime = unixtime - (2922*24*60*60)  # Amiga epoch starts 1978-01-01
    mdays = int(_utime / (24*60*60))     # Days since 1978-01-01
    _utime -= mdays * (24*60*60)
    mmins = int(_utime / 60)             # Minutes
    _utime -= mmins * 60
    mticks = _utime * 50                 # Ticks of 1/50 sec

    filetype = 3 # Regular file

    data = struct.pack('!LLLLLLLB',
                       29 + len(path) + 6,  # Length of this message, really
                       filelen,
                       0,
                       amigaattrs,
                       mdays,
                       mmins,
                       mticks,
                       filetype)
    data += path
    data += b'\0\0\0\0\0\0'  # No idea what this is for
    session.sendMsg(0x66, data)

    # TODO: Handle target FS full
    # TODO: Handle permission denied on target FS

    AEMultipart.send(session, filebody)
    close(session)



# Command 0x67
# Delete a path.
# Can be a file or folder, and will be deleted recursively.
#
def delete(session, path):
    print("AECmds.delete: " + path)

    session.sendMsg(0x67, path + b'\x00')

    (type, _) = session.recvMsg()

    close(session)

    # type == 0 means the file was deleted successfully
    return (type == 0)



# Command 0x68
# Rename a file, leaving it in the same folder.
#
def rename(session, path, new_name):
    print("AECmds.rename: " + path + ' - ' + new_name)
    session.sendMsg(0x68, path + b'\x00' + new_name + b'\x00')
    (type, _) = session.recvMsg()

    if type != 0:
        print("AECmds.rename: Response type " + str(type))

    close(session)

    # Assume that type == 0 means the file was renamed successfully
    return (type == 0)



# Command 0x69
# Move a file from a folder to a different one, keeping its name.
#
def move(session, path, new_parent):
    print("AECmds.move: " + path + ' - ' + new_parent)
    session.sendMsg(0x69, path + b'\x00' + new_parent + b'\x00\xc9')
    (type, _) = session.recvMsg()

    if type != 0:
        print("AECmds.move: Response type " + str(type))

    close(session)

    # Assume that type == 0 means the file was moved successfully
    return (type == 0)



# Command 0x6a
# Copy a file.
#
def copy(session, path, new_parent):
    print("AECmds.copy: " + path + ' - ' + new_parent)
    session.sendMsg(0x6a, path + b'\x00' + new_parent + b'\x00\xc9')
    (type, _) = session.recvMsg()

    if type != 0:
        print("AECmds.copy: Response type " + str(type))

    close(session)

    # Assume that type == 0 means the file was copied successfully
    return (type == 0)



# Command 0x6b
# Set attributes and comment.
#
def setattr(session, amigaattrs, path, comment):
    print("AECmds.setattr: " + str(amigaattrs) + ' - ' + path + ' - ' + comment)

    data = struct.pack('!L', amigaattrs)
    data += path + b'\x00'
    data += comment + b'\x00'
    data += struct.pack('!L', 0)

    session.sendMsg(0x6b, data)
    (type, _) = session.recvMsg()

    if type != 0:
        print("AECmds.setattr: Response type " + str(type))

    close(session)

    # Assume that type == 0 means the file was copied successfully
    return (type == 0)



# Command 0x6c
# Request (?)
#



# Command 0x6d
# Finish a running operation.
#
def close(session):
    print('AECmds.close')

    session.sendMsg(0x6d, b'')

    (type, data) = session.recvMsg()
    assert type == 0x0a
    if data != b'\0\0\0\0\0':
        print('AECmds.close: data == ' + binascii.hexlify(data))
    # Format of data returned:
    # Byte 0: ?
    # Byte 1: ?
    # Byte 2: ?
    # Byte 3: 00 - No error
    #         06 - File no longer exists
    #         1c - Timed out waiting for host to request next read block
    # Byte 4: Path in case of error 06.
    #         Empty (null-terminated) otherwise?
    #         Null-terminated string.
    #assert data == b'\0\0\0\0\0'



# Command 0x6e
# Format a disk.
#



# Command 0x6f
# Create a new folder and matching .info file.
# This folder will be named "Unnamed1".
#
