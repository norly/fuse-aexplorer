import binascii
from errno import ENOENT, EINVAL, EIO, EROFS
from fusepy import FUSE, FuseOSError, Operations
from stat import S_IRUSR, S_IWUSR, S_IXUSR, S_IRGRP, S_IROTH, S_IXGRP, S_IXOTH, S_IFDIR, S_IFREG
import struct
import sys
from time import time

from AELink import AELinkSerial
from AESession import AESession
import AEMultipart
import AECmds
from FuseCache import FuseCache
import FusePatches


amiga_charset = 'iso8859-1'








class AEFuse(Operations):
    def __init__(self, session):
        self.session = session

        self.cache = FuseCache()

        self.readpath = None
        self.readbuf = None
        self.readmax = None # Total size of the file being read

        self.writepath = None
        self.writebuf = None
        self.writemtime = None
        self.writeattrs = None


    def getattr(self, path, fh=None):
        print('AEFuse.getattr: ' + path)

        dirpath = path[0:path.rfind('/')]  # Without the trailing slash
        name = path[path.rfind('/') + 1:]  # Without a leading slash

        st = self.cache.getattr(path)

        if not st:
            # If we have a cache miss, see if we've cached its parent
            # directory.
            #
            # If not, then try to read the parent directory.
            #
            # Note that accessing a deep path will cause Linux to stat its
            # parents recursively, which in turn will cause self.getattr()
            # to call self.readdir() on them, filling all cache levels in
            # between.
            #
            # https://sourceforge.net/p/fuse/mailman/message/19717106/
            #
            if self.cache.getkids(dirpath) == None:
                # We haven't read the directory yet
                if name in self.readdir(dirpath, fh):
                    # If the dirlist succeeded, try again.
                    #
                    # Note that we're never asking the host for a deep path
                    # that doesn't exist, since Linux will stat all parents,
                    # thus listing directories at every level until the first
                    # one that doesn't exist (see above).
                    #
                    # As a bonus, this automatically updates the cache if the
                    # path now exists.
                    return self.getattr(path, fh)

            # Okay, the path doesn't exist.
            # That means our file can't exist.
            print('getaddr ENOENT: ' + path)
            raise FuseOSError(ENOENT)

        return st


    def readdir(self, path, fh):
        print("AEFuse.readdir: " + path)

        self._cancel_read()
        self._flush_write()

        # Request directory listing
        kids = AECmds.dir_list(self.session, path[1:].encode(amiga_charset))

        # Update cache
        self.cache.setkids(path, kids)

        #return [(name, self.cache[name], 0) for name in self.cache.keys()]
        return kids.keys()


    def read(self, path, size, offset, fh):
        print("AEFuse.read: " + path + ' -- ' + str(size) + ' @ ' + str(offset))

        # Avoid inconsistency.
        # If we don't do this, then reading the file while it's open
        # returns something different from what is in the write buffer.
        self._flush_write()

        if self.readpath != path:
            if self.readpath != None:
                self._cancel_read()

            self.readpath = path
            self.readbuf = b''

            # Request file
            self.readmax = AECmds.file_read_start(self.session, path[1:].encode(amiga_charset))

            # TODO: Check for None returned, meaning that the path doesn't exist.

        if (offset + size > len(self.readbuf)) \
        and (offset < self.readmax) \
        and (len(self.readbuf) < self.readmax):
            # Get further file contents if we need it.
            while len(self.readbuf) < min(offset + size, self.readmax):
                (blockOffset, blockData) = AECmds.file_read_next(self.session)

                if blockData == None:
                    # Since we only enter this loop if there should be data
                    # left to read, a None returned means an unexpected EOF
                    # or more probably, the connection timed out.
                    #
                    # We operate under the illusion that we can keep the last
                    # accessed file open wherever we were at, however after a
                    # few seconds the host will close the file without us
                    # knowing. In case that happens, let's reload the file.
                    print('Unexpected error while reading next file block.')
                    print('Re-requesting file.')

                    # If we cancel the transfer ourselves, then the reply to
                    # sendClose() will be 0x00 0x00 0x00 0x1c 0x00.
                    #
                    # Strange: If we cancel in the same situation, but without
                    # having received the type 1 cancel message from the host,
                    # the reply to sendClose() is normal zeroes.
                    self._cancel_read()
                    return self.read(path, size, offset, fh)

                assert blockOffset == len(self.readbuf)
                self.readbuf += blockData

            # When done transferring a whole file, the Amiga side insists on
            # sending its end-of-file type 4 message. So let's request it.
            if len(self.readbuf) == self.readmax:
                (blockOffset, blockData) = AECmds.file_read_next(self.session)
                assert blockData == None

        print("read: " + path + ' -- finished with len(self.readbuf) == ' + str(len(self.readbuf)))
        return self.readbuf[offset:offset + size]


    def _cancel_read(self):
        # Cancel current read operation
        if self.readpath != None:
            if (len(self.readbuf) < self.readmax):
                print('_cancel_read: Cancelling.')
                AECmds.cancel(self.session)

            AECmds.close(self.session)

            self.readbuf = None
            self.readpath = None


    def open(self, path, flags):
        print("AEFuse.open: " + path)

        # Dummy function to allow file access.

        return 0


    def _prep_write(self, path, trunclen):
        # We can't write in the virtual top level directory
        if len(path) < 4:
            raise FuseOSError(ENOENT)

        self._cancel_read()

        if self.writepath != path:
            self._flush_write()

            # If the file already exists, read its previous contents.
            # Check cache, since FUSE/VFS will have filled it.
            st = self.cache.getattr(path)
            if st != None and st['st_size'] > 0:
                if trunclen != None:
                    if trunclen > 0:
                        self.writebuf = self.read(path, trunclen, 0, None)
                else:
                    self.writebuf = self.read(path, st['st_size'], 0, None)
                self._cancel_read()

            self.writepath = path
            self.writeattrs = 0
            if self.writebuf == None:
                self.writebuf = b''


    def create(self, path, mode, fi=None):
        print("AEFuse.create: " + path)

        # We can't write in the virtual top level directory
        if len(path) < 4:
            raise FuseOSError(ENOENT)

        # We can't create a file over an existing one.
        # By now, the system will have primed our cache, so we won't ask
        # the big fuseop self.getattr(). That wouldn't work anyway, since
        # it raises a FuseOSError rather than returning None.
        assert self.cache.getattr(path) == None
        if self.writepath != None:
            assert path != self.writepath

        # Create a dummy file, so the path exists
        AECmds.file_write(self.session, path[1:].encode(amiga_charset), 0, time(), b'')

        # Refresh cache so a subsequent getattr() succeeds
        dirpath = path[0:path.rfind('/')]
        self.readdir(dirpath, None)

        return 0


    def truncate(self, path, length, fh=None):
        print("AEFuse.truncate: " + path + ' -- ' + str(length))

        self._prep_write(path, length)

        self.writebuf = self.writebuf[:length]
        if length > len(self.writebuf):
            # Fill up
            self.writebuf = self.writebuf[:len(self.writebuf)] + (b'\0' * (length - len(self.writebuf)))

        self.writemtime = time()

        return 0



    # WARNING: Due to buffering, we will NOT be able to report
    #          a full disk as a response to the write call!
    def write(self, path, data, offset, fh):
        print("AEFuse.write: " + path + ' -- ' + str(len(data)) + ' @ ' + str(offset))

        self._prep_write(path, None)

        if offset > len(self.writebuf):
            # Fill up
            self.writebuf = self.writebuf[:len(self.writebuf)] + (b'\0' * (offset - len(self.writebuf)))

        self.writebuf = self.writebuf[:offset] + data + self.writebuf[offset+len(data):]
        self.writemtime = time()

        # WARNING!
        # We cannot check for a full disk here, so we're
        # just assuming that buffering is fine.
        return len(data)


    def utimens(self, path, (atime, mtime)):
        print("AEFuse.utimens: " + path + ' -- ' + str(mtime))

        # We can only set the time when sending a complete file.
        if self.writepath == path:
            self.writemtime = mtime
        else:
            raise FuseOSError(EROFS)


    def _flush_write(self):
        if self.writepath == None:
            return

        # If this fails, there is nothing we can do.
        # Except returning an error on close().
        # But honestly, who checks for that?
        AECmds.file_write(self.session,
                          self.writepath[1:].encode(amiga_charset), self.writeattrs,
                          self.writemtime, self.writebuf)

        # Extract dirpath before we throw away self.writepath
        dirpath = self.writepath[0:self.writepath.rfind('/')]

        # Throw away the write buffer once done, so we don't cache full files.
        self.writepath = None
        self.writebuf = None
        self.writemtime = None
        self.writeattrs = None

        # Refresh cache so subsequent accesses are correct
        self.readdir(dirpath, None)


    # Called on close()
    def flush(self, path, fh):
        print("AEFuse.flush: " + path)

        # Flush any remaining write buffer
        self._flush_write()

        print("AEFuse.flush: finished: " + path)


    def unlink(self, path):
        print("AEFuse.unlink: " + path)

        # TODO: Handle file that is currently open for reading/writing

        self.session.sendMsg(0x67, path[1:].encode(amiga_charset) + b'\x00')

        (type, _) = self.session.recvMsg()

        self.session.sendClose()

        # Refresh cache so a subsequent getattr() is up to date.
        # We refresh even in case the delete failed, because it
        # indicates our cache being out of date.
        dirpath = path[0:path.rfind('/')]
        self.readdir(dirpath, None)

        if type == 0:
            return 0  # File deleted successfully
        else:
            raise FuseOSError(EIO)


    def rmdir(self, path):
        # TODO: Refuse if the directory is not empty
        return self.unlink(path)


    def ae_mkdir(self, path):
        self._cancel_read()

        amigaattrs = 0

        _utime = time() - (2922*24*60*60) # Amiga epoch starts 1978-01-01
        mdays = int(_utime / (24*60*60))  # Days since 1978-01-01
        _utime -= mdays * (24*60*60)
        mmins = int(_utime / 60)          # Minutes
        _utime -= mmins * 60
        mticks = _utime * 50              # Ticks of 1/50 sec

        filetype = 2 # Folder

        data = struct.pack('!LLLLLLLB',
                           29 + len(path) + 6,  # Length of this message, really
                           0,
                           0,
                           amigaattrs,
                           mdays,
                           mmins,
                           mticks,
                           filetype)
        data += path.encode(amiga_charset)
        data += b'\0\0\0\0\0\0'  # No idea what this is for
        self.session.sendMsg(0x66, data)

        # TODO: Handle target FS full
        # TODO: Handle permission denied on target FS

        self.session.sendClose()


    def mkdir(self, path, mode):
        print('AEFuse.mkdir: ' + path)

        self.ae_mkdir(path[1:].encode(amiga_charset))

        # Refresh cache so a subsequent getattr() succeeds
        dirpath = path[0:path.rfind('/')]
        self.readdir(dirpath, None)


    def rename(self, old, new):
        print('AEFuse.rename: ' + old + ' - ' + new)
        dirpath_old = old[0:old.rfind('/')]
        dirpath_new = new[0:new.rfind('/')]
        filename_old = old[old.rfind('/') + 1:]
        filename_new = new[new.rfind('/') + 1:]

        # If the file already exists, delete it.
        # Check cache, since FUSE/VFS will have filled it.
        st = self.cache.getattr(new)
        if st != None:
            self.unlink(new)

        if dirpath_new == dirpath_old:
            AECmds.rename(self.session,
                      old[1:].encode(amiga_charset),
                      filename_new.encode(amiga_charset))
        else:
            # Move in 3 steps:
            # 1. Rename file to a temporary name
            #    (NOTE: We hope it doesn't exist!)
            # 2. Move the file to the new folder
            # 3. Rename the file to the target file name
            # The reason for this is that the old file name may exist in
            # the new directory, and the new file name may exist in the
            # old directory. Thus, if we were to do only one renaming,
            # either order of rename+move or move+rename could be
            # problematic.

            assert (self.cache.getattr(dirpath_old + '/_fatemp_') == None)
            assert (self.cache.getattr(dirpath_new + '/_fatemp_') == None)

            AECmds.rename(self.session,
                      old[1:].encode(amiga_charset),
                      '_fatemp_'.encode(amiga_charset))
            AECmds.move(self.session,
                        (dirpath_old + '/_fatemp_')[1:].encode(amiga_charset),
                        dirpath_new[1:].encode(amiga_charset))
            AECmds.rename(self.session,
                      (dirpath_new + '/_fatemp_')[1:].encode(amiga_charset),
                      filename_new.encode(amiga_charset))

        # Refresh cache so a subsequent getattr() succeeds
        self.readdir(dirpath_old, None)
        self.readdir(dirpath_new, None)


    def chmod(self, path, mode):
        print("AEFuse.chmod: " + path + ' -- ' + str(mode))

        amigaattrs = 0
        # Apparently we don't have to worry about directory flags
        if not mode & S_IRUSR: amigaattrs |= 0x08
        if not mode & S_IWUSR: amigaattrs |= 0x04
        if not mode & S_IXUSR: amigaattrs |= 0x02

        AECmds.setattr(self.session,
                       amigaattrs,
                       path[1:].encode(amiga_charset),
                       '')


    def chown(self, path, uid, gid):
        # AmigaOS does not know users/groups.
        raise FuseOSError(EROFS)


    # Called on umount
    def destroy(self, path):
        print('AEFuse.destroy: ' + path)

        # Flush any remaining write buffer
        self._cancel_read()
        self._flush_write()
