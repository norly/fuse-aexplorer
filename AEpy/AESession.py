import binascii
import serial
import struct


class AESession:
    def __init__(self, link):
        self.link = link
        self.seq = 1
        self.sendInit()
        self.packetsize = 512


    def recvMsg(self):
        rawHeader = self.link.recv(12)
        if len(rawHeader) != 12:
            print('recvMsg: len(rawHeader) == ' + str(len(rawHeader)) + ' data: ' + binascii.hexlify(rawHeader))
        #assert len(rawHeader) == 12

        (type, datalen, seq, crc) = struct.unpack('!HHLL', rawHeader)
        assert crc == (binascii.crc32(rawHeader[0:8]) & 0xffffffff)
        # TODO: Send PkRs if CRC mismatches

        data = b''

        if datalen > 0:
            data = self.link.recv(datalen)
            assert len(data) == datalen

            # Note: Python calculates signed CRCs.
            #       Thus, we parse the incoming CRC as signed.
            datacrc = self.link.recv(4)
            assert len(datacrc) == 4
            (datacrc,) = struct.unpack('!L', datacrc)

            assert datacrc == (binascii.crc32(data) & 0xffffffff)
            # TODO: Send PkRs if CRC mismatches

        self.link.send(b'PkOk')

        # seq is currently ignored when receiving
        return (type, data)


    def sendMsg(self, type, data):
        stream = struct.pack('!HHL', type, len(data), self.seq)
        stream += struct.pack('!L', binascii.crc32(stream) & 0xffffffff)

        if len(data) > 0:
            stream += data
            stream += struct.pack('!L', binascii.crc32(data) & 0xffffffff)

        self.link.send(stream)

        # TODO: Re-send on 'PkRs'
        assert self.link.recv(4) == b'PkOk'

        self.seq += 1;



    def sendInit(self):
        self.sendMsg(2, b'Cloanto(r)')
        # TBD: Password support.
        #      It is CRC32'd and the CRC is appended to the string above.

        # TODO: Recover from desynced state
        #if not self.isAcked():
        #    self.sendAck()
        #    return self.sendInit()

        (type, data) = self.recvMsg()
        assert type == 2
        assert data.startswith(b'Cloanto')


    def sendClose(self):
        print('sendClose')

        self.sendMsg(0x6d, b'')

        (type, data) = self.recvMsg()
        assert type == 0x0a
        if data != b'\0\0\0\0\0':
            print('sendClose: data == ' + binascii.hexlify(data))
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
