import struct



def recvHeader(session):
    (type, data) = session.recvMsg()
    # TODO: Check for type 1, as that means an error.
    #       For example, a directory can't be listed because it doesn't exist.
    assert type == 3
    assert len(data) == 8

    (datalen, pktsize) = struct.unpack('!LL', data)

    return (datalen, pktsize)


def recvBlock(session):
    # Send empty type 0 message to request next block
    session.sendMsg(0, b'')

    (type, data) = session.recvMsg()

    if type == 1:
        print('recvMultipartBlock: Host cancelled transfer.')
        # Maybe TODO: Raise an exception
        return (None, None)

    if type == 4:
        # Last block
        assert len(data) == 0
        return (None, None)

    # Expect a data block
    assert type == 5

    # Any data block has the offset prepended,
    # followed by up to PACKETSIZE-4 bytes of payload.
    assert len(data) >= 4

    (offset,) = struct.unpack('!L', data[0:4])

    return (offset, data[4:])


def recv(session):
    fullData = b''

    (datalen, pktsize) = recvHeader(session)

    offset = 0
    data = b''
    while data != None:
        assert offset == len(fullData)
        fullData += data

        (offset, data) = recvBlock(session)

    return fullData


def send(session, fullData):
    # Wait for Amiga to request first block with type 0
    (type, _) = session.recvMsg()

    # TODO: Handle transfer abort (type 1)
    # TODO: What happens when sending an ADF != 901120 bytes?
    assert (type == 0) or (type == 8)

    if type == 8:
        # Does this confirm that we want to overwrite?
        session.sendMsg(0, b'')

    # Send length and block size
    session.sendMsg(3, struct.pack('!LL', len(fullData), session.packetsize))

    bytesSent = 0
    while bytesSent < len(fullData):
        # Wait for Amiga to request block with type 0
        (type, _) = session.recvMsg()
        assert type == 0

        print("AEMultipart.send: " + str(bytesSent))

        txlen = min(session.packetsize - 4, len(fullData) - bytesSent)
        session.sendMsg(5, struct.pack('!L', bytesSent) + fullData[bytesSent : bytesSent+txlen])

        bytesSent += txlen

    # Wait for Amiga's type 0
    (type, _) = session.recvMsg()
    assert type == 0

    # Finish transfer
    session.sendMsg(4, b'')
