#!/usr/bin/env python
#
#   Incredibly hacky and limited CI-V Implementation for the IC-7610
#   Allowing setting of VFOs A and B.
#
import codecs
import serial
import time

from threading import Lock


class CIV(object):

    def __init__(
        self,
        port="/dev/tty.SLAB_USBtoUART",
        baudrate=115200,
        addr=0x98
    ):

        self.addr = addr
        self.lock = Lock()
        try:
            self.s = serial.Serial(port, baudrate, timeout=1)
            self.s.rts = False
            self.s.dtr = False
        except Exception as e:
            print("Error: " + str(e))


    def close(self):
        self.s.close()
    
    def send_cmd(self,
        command = 0x00,
        subcommand = 0x00,
        data = b'\x00'):

        _cmd = b'\xFE\xFE' + bytes([self.addr, command, subcommand]) 
        
        _cmd += data + b'\xFD'

        #print(_cmd)
        self.s.write(_cmd)
        time.sleep(0.01)

    def itobcd(self, i):
        """ Input MUST be in Hz"""

        i = int(i)
        i_str = f"{i:010d}"
        out = r'\x' + i_str[8] + i_str[9] + r'\x' + i_str[6] + i_str[7] + r'\x' + i_str[4] + i_str[5] + r'\x' + i_str[2] + i_str[3] + r'\x' + i_str[0] + i_str[1]
        return codecs.escape_decode(out)[0]

    def set_freq_vfo(self, vfo, frequency):
        _freq = self.itobcd(frequency)

        if vfo == 'A':
            _data = b'\x00' + _freq
            self.send_cmd(command=0xE0,subcommand=0x25,data=_data)
        else:
            _data = b'\x01' + _freq
            self.send_cmd(command=0xE0,subcommand=0x25,data=_data)
    

    def set_freq(self, frequency):
        self.set_freq_vfo('A', frequency)

    def set_a(self, frequency):
        self.set_freq_vfo('A', frequency)

    def set_b(self, frequency):
        self.set_freq_vfo('B', frequency)


if __name__ == "__main__":
    radio = CIV()
    time.sleep(1)

    #radio.setvfo('B')
    radio.set_freq_vfo('A',7067000)
    time.sleep(1)
    radio.set_freq_vfo('B',14067000)
    #radio.setvfo('A')