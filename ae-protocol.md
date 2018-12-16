Message types
==============

     Msg ID | Sending side | Description
    --------|--------------|----------------------------------
         00 | Ami/PC       | Ask for next block
         01 | Ami/PC       | Transfer cancelled
         02 | Ami/PC       | Initialisation / Init response
         03 | Ami/?        | Multipart header
         04 | Amiga        | EOF (no payload)
         05 | Amiga        | Next data block

         08 | Amiga        | File already exists (when trying to write with 0x66)
	 09 | Amiga        | Size ? (response to 0x6c)
         0a | Amiga        | Close response
         0b | Amiga        | Format response?

         64 | PC           | List directory
         65 | PC           | File read
         66 | PC           | File/folder write
         67 | PC           | File/folder delete (recursively)
         68 | PC           | File rename (name changes) (works on drives, too?)
         69 | PC           | File move (path changes)
         6a | PC           | File copy
         6b | PC           | Set attributes and comment
         6c | PC           | Request size on disk (?)
         6d | PC           | Close file
         6e | PC           | Format disk (needs Kickstart 2.0 or newer)
         6f | PC           | New folder




Request details
================

64 - List a directory
----------------------

### TODO ###


65 - Read a file
-----------------

### TODO ###


66 - Write a file
------------------

### TODO ###


67 - Delete file/folder
------------------------

Payload:

     Bytes | Content
    -------|--------------------
         n | Path
         1 | 0x00

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).

If Path is a folder, it will be deleted together with its contents.


68 - Rename file/folder
------------------------

Payload:

     Bytes | Content
    -------|--------------------
         n | Path (including old file name)
         1 | 0x00
         n | New file name (without path)
         1 | 0x00

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).


69 - Move file/folder
----------------------

Payload:

     Bytes | Content
    -------|--------------------
         n | Path (including old file name)
         1 | 0x00
         n | New path to contain file (folder without trailing slash or file name)
         1 | 0x00
	 1 | 0xc9 (?)

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).

If Path is a folder, it will be moved together with its contents.
This command appears to work across devices.


6a - Copy file/folder
----------------------

Payload:

     Bytes | Content
    -------|--------------------
         n | Path (including old file name)
         1 | 0x00
         n | New path to contain file (folder without trailing slash or file name)
         1 | 0x00
	 1 | 0xc9 (?)

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).

If Path is a folder, it will be moved together with its contents.
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



6d - Close file
----------------

No payload.

Then, read type 0x0a for confirmation (typical payload: 5 bytes of 0x00).

This is used to finish an operation, such as a directory listing
or renaming a file.


6e - Format disk
-----------------

### TODO ###


6f - New folder
----------------

Payload:

     Bytes |  Content
    -------|--------------------
         n | Parent path
         1 | 0x00

Then, read type 0 for confirmation.
Then, sendClose() (0xa response: 5x 00).

The host will create a new folder in the given path, together with a
matching .info file.
The folder name cannot be chosen, and will be something like "Unnamed1".

To create a folder with a specific name, use 0x66.
Note that 0x66'ing a folder does not seem to set its time.
