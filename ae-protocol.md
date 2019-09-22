Overview
========

The AE protocol works by exchanging messages between the Amiga and the Client (e.g. an IBM PC).

Each message consists of a header and optionally payload data. Both parts carry CRC32 checksums
to ensure data integrity.

Message header
--------------

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| 2              | Msg (see below)              |
| 2              | Payload length               |
| 4              | Sequence                     |
| 4              | CRC32                        |

Payload (if any)
----------------

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| n              | Payload                      |
| 4              | CRC32                        |

Each message is acknowledged by the receiving side by a 4-Byte "PkOk" response if the checksum matches, "PkRs" otherwise.

Recovery from checksum errors: on "PkRs" non-ack, the sending side re-sends the whole message until "PkOk" is received.
FIXME: is this correct?

Message types
=============

| Msg  | ID                | Sending side | Description                                               |
| ---- | ----------------- | ------------ | --------------------------------------------------------- |
| 0x00 | MSG_NEXT_PART     | Amiga/Client | Ask for next block                                        |
| 0x01 |                   | Amiga/Client | Transfer cancelled                                        |
| 0x02 | MSG_INIT          | Amiga/Client | Initialisation / Init response                            |
| 0x03 | MSG_MPARTH        | Amiga/?      | Multipart header                                          |
| 0x04 | MSG_EOF           | Amiga        | EOF (no payload)                                          |
| 0x05 | MSG_BLOCK         | Amiga        | Next data block                                           |
|      |                   |              |                                                           |
| 0x08 | MSG_IOERR         | Amiga        | File already exists (when trying to write with 0x66)      |
| 0x09 |                   | Amiga        | Size ? (response to 0x6c)                                 |
| 0x0a | MSG_ACK_CLOSE     | Amiga        | Close response                                            |
| 0x0b |                   | Amiga        | Format response?                                          |
|      |                   |              |                                                           |
| 0x64 | MSG_DIR           | Client       | List directory                                            |
| 0x65 | MSG_FILE_SEND     | Client       | File read                                                 |
| 0x66 | MSG_FILE_RECV     | Client       | File/dir write                                            |
| 0x67 | MSG_FILE_DELETE   | Client       | File/dir delete (recursively )                            |
| 0x68 | MSG_FILE_RENAME   | Client       | File/dir rename                                           |
| 0x69 | MSG_FILE_MOVE     | Client       | File move (path changes)                                  |
| 0x6a | MSG_FILE_COPY     | Client       | File copy                                                 |
| 0x6b |                   | Client       | Set attributes and comment                                |
| 0x6c |                   | Client       | Request size on disk (?)                                  |
| 0x6d | MSG_FILE_CLOSE    | Client       | Close file                                                |
| 0x6e |                   | Client       | Format disk (needs Kickstart 2.0 or newer)                |
| 0x6f |                   | Client       | New directory                                             |

Message details
===============

0x00 MSG_NEXT_PART - Ask for next block
---------------------------------------

Payload: none

Expected repsonse: MSG_BLOCK or MSG_EOF


0x03 MSG_MPARTH - Multipart header
----------------------------------

Payload:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| 4              | length                       |
| 4              | 0x000002000 FIXME ??         |

Expected response: 0x00 MSG_NEXT_PART

0x04 MSG_EOF
------------

Payload: none

Expected response: 0x6d MSG_FILE_CLOSE

0x05 MSG_BLOCK - Next data block
--------------------------------

Payload:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| 4              | offset                       |
| n              | data                         |

Expected response: 0x00 MSG_NEXT_PART

0x08 MSG_IOERR - I/O Error
--------------------------

Payload: none

Sent in response to various commands if operation could not be completed
or if file already exists (when trying to write with 0x66 MSG_FILE_RECV).

0x64 MSG_DIR - List a directory (Client -> Amiga)
-------------------------------------------------

Payload:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| n              | path                         |
| 1              | 0                            |
| 1              | 1 FIXME ??                   |

Expected response: 0x03 MSG_MPARTH if path exists, 0x04 MSG_EOF otherwise

Multipart data will be polled in chunks using 0x00 MSG_NEXT_PART. This data is structured as follows:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| 4              | number of entries            |
| n              | dir entries                  |

Each dir entry is structured as follows:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| 4              | len (29+n+m)                 |
| 4              | size                         |
| 4              | used                         |
| 2              | type FIXME ???               |
| 2              | attributes                   |
|                |   S: 0x40                    |
|                |   P: 0x20                    |
|                |   A: 0x10                    |
|                |   R: 0x08                    |
|                |   W: 0x04                    |
|                |   E: 0x02                    |
|                |   D: 0x01                    |
| 4              | date                         |
| 4              | time                         |
| 4              | ctime                        |
| 1              | type2 (0x00 file, 0x02 dir)  |
| n              | name\0                       |
| m              | comment\0                    |


0x65 MSG_FILE_SEND - Read a file
--------------------------------

Payload: filename\0

Expected response: 0x08 MSG_IOERR if file cannot be opened, 0x03 MSG_MPARTH otherwise


0x66 MSG_FILE_RECV - Write a file (Client -> Amiga)
---------------------------------------------------

Payload:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| 4              | header size                  |
| 4              | file size                    |
| 4              | FIXME ??                     |
| 4              | attributes                   |
|                |   S: 0x40                    |
|                |   P: 0x20                    |
|                |   A: 0x10                    |
|                |   R: 0x08                    |
|                |   W: 0x04                    |
|                |   E: 0x02                    |
|                |   D: 0x01                    |
| 4              | date (hours since 1/1/78)    |
| 4              | time (mins since midnight)   |
| 4              | ctime                        |
| 1              | file type                    |
|                |   2: directory               |
|                |   3: regular file            |
| header_size-29 | file name                    |

Expected response: 0x00 MSG_NEXT_PART if file does not exist (yet), 0x08
MSG_IOERR otherwise. 

If this is a regular file, file contents will be transferred using 0x03
MSG_MPARTH/0x05 MSG_BLOCK. Once file is transferred completely, 0x6d
MSG_FILE_CLOSE will be sent by the client. If this is a directory, 0x6d
MSG_FILE_CLOSE will be sent by the client right away.

0x67 MSG_FILE_DELETE - File/dir delete (recursively)
----------------------------------------------------

Payload:

| Bytes          | Content                      |
| -------------- | ---------------------------- |
| n              | Path                         |
| 1              | 0x00                         |

Expected response: 0x00 MSG_NEXT_PART. Then, 0xa MSG_FILE_CLOSE.

If Path is a dir, it will be deleted together with its contents.


0x68 MSG_FILE_RENAME - Rename file/dir
--------------------------------------

Payload:

| Bytes          | Content                        |
| -------------- | ------------------------------ |
| n              | Path (including old file name) |
| 1              | 0x00                           |
| m              | New file name (without path)   |
| 1              | 0x00                           |

Expected response: 0x00 MSG_NEXT_PART. Then, send 0x6d MSG_FILE_CLOSE.

Seems to work on volumes (disk rename), too.

0x69 MSG_FILE_MOVE - File move (path changes)
---------------------------------------------

Payload:

| Bytes          | Content                                                            |
| -------------- | ------------------------------------------------------------------ |
| n              | Path (including old file name)                                     |
| 1              | 0x00                                                               |
| m              | New path to contain file (dir without trailing slash or file name) |
| 1              | 0x00                                                               |
| 1              | 0xc9 FIXME (?)                                                     |

Expected response: 0x00 MSG_NEXT_PART. Then, send 0x6d MSG_FILE_CLOSE (0xa response: 5x 00).

If Path is a directory, it will be moved together with its contents.
This command appears to work across devices.


0x6a MSG_FILE_COPY - File copy
------------------------------

Payload:

| Bytes          | Content                                                            |
| -------------- | ------------------------------------------------------------------ |
| n              | Path (including old file name)                                     |
| 1              | 0x00                                                               |
| m              | New path to contain file (dir without trailing slash or file name) |
| 1              | 0x00                                                               |
| 1              | 0xc9 FIXME (?)                                                     |

Expected response: 0x00 MSG_NEXT_PART. Then, send 0x6d MSG_FILE_CLOSE (0xa response: 5x 00).

If Path is a directory, it will be copied together with its contents.
This command appears to work across devices.


6b - Set attributes and comment
--------------------------------

Payload:

     Bytes | Content
    -------|--------------------
         4 | Attributes
         n | Path
         1 | 0x00
         n | Comment
         1 | 0x00
         4 | Checksum? (seems to be 0x00000000 if comment empty)

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).


6c - Request size on disk (?)
------------------------------------

Payload:

     Bytes | Content
    -------|--------------------
         n | Path
         1 | 0x00

Then, read type 0 for confirmation.
Then, read type 9 for 12 bytes of payload (### TODO ###).
Then, send type 0 to request more data (no payload).
Then, read type 9 for 12 bytes of payload (### TODO ###).
Then, send type 0 to request more data (no payload).
Then, read type 0 signaling end of attributes (no payload).
Then, sendClose() (0xa response: 5x 00).

OR

Then, read type 0 for confirmation.
Then, read type 0 signaling end of attributes (no payload).
Then, sendClose() (0xa response: 5x 00).



0x6d MSG_FILE_CLOSE - Close file
--------------------------------

No payload.

Then, read type 0x0a MSG_ACK_CLOSE for confirmation (typical payload: 5 bytes of 0x00).

This is used to finish an operation, such as a directory listing
or renaming a file.


6e - Format disk
-----------------

### TODO ###


6f - New directory
------------------

Payload:

     Bytes |  Content
    -------|--------------------
         n | Parent path
         1 | 0x00

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).

The host will create a new directory in the given path, together with a
matching .info file.
The directory name cannot be chosen, and will be something like "Unnamed1".

To create a directory with a specific name, use 0x66.
Note that 0x66'ing a directory does not seem to set its time.

