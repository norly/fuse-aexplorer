import binascii
import serial
import struct
import traceback


class AELink:
    def __init__(self):
        return





class AELinkSerial(AELink):
    def __init__(self, path, speed):
        self.ser = serial.Serial(path, speed, timeout=5, rtscts=1)
        assert self.ser.name == path

        AELink.__init__(self)

    def recv(self, rxlen):
        assert self.ser.is_open
        buf = self.ser.read(rxlen)
        #print("Received: " + binascii.hexlify(buf))
        return buf

    def send(self, data):
        assert self.ser.is_open
        #print("Sending: " + binascii.hexlify(data))
        #traceback.print_stack()
        return self.ser.write(data)

    def close(self):
        assert self.ser.is_open
        self.ser.close()
