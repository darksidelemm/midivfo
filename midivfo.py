#!/usr/bin/env python
#
#   Stupid hack to turn a very expensive Amateur Radio into a Monophonic Synth.

#   Author: Mark Jessop <vk5qi@rfhead.net>

#   Dependencies:
#    * Python 3
#    * python-rtmidi
#    * Hamlib (in particular rigctld)

#   Setup:
#    * Set a signal generator up on a known frequency (aligned with the rig you are using). In my case I used 14067000 Hz
#    * Run up rigctld setup to talk to your radio. In my care I run:
#      rigctld -m 378 -r /dev/tty.SLAB_USBtoUART -s 115200
#    * Set radio into Upper-Sideband Mode (USB)

#   Operation:
#    * Run up this utility with: python mifivfo.py --cw 14067000
#    * If your midi device is not #0, then set it with --midi
#    * Play!

#   TODO:
#    * Multiple VFOs? Doesn't look like hamlib has support for my 7610's two VFOs :-(


import argparse
import math
import socket
import sys
import time

from rtmidi.midiutil import open_midiinput

# Read command-line arguments
parser = argparse.ArgumentParser(description="MIDI to VFO", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--cw", type=int, default=14067000, help="CW Reference Frequency to tune around, in Hz.")
parser.add_argument("--midi", type=int, default=0, help="MIDI Device Number")
args = parser.parse_args()


CW_TONE = args.cw
# Assuming that if we tune above the CW tone that there will be no signal.
# Might not be the case, but that just makes things interesting :-)
OFF_TONE = CW_TONE + 300

class RIGCTLD(object):
    """ rigctld (hamlib) communication class """

    def __init__(self, 
        hostname="127.0.0.1", 
        port=4532, 
        timeout=5,
        vfos = 1):

        """ Initiate the RIGCTLD Connection """
        self.hostname = hostname
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)

        self.connect()


    def connect(self):
        """ Connect to rigctld instance """
        self.sock.connect((self.hostname,self.port))
        model = self.get_model()
        if model == None:
            # Timeout!
            self.close()
            raise Exception("Timeout!")
        else:
            return model


    def close(self):
        self.sock.close()


    def send_command(self, command):
        """ Send a command to the connected rigctld instance,
            and return the return value.
        """
        _command = command + '\n'
        self.sock.sendall(_command.encode('ascii'))
        try:
            return self.sock.recv(1024).decode('ascii')
        except:
            return None


    def set_vfo(self, freq):
        """ Set the main VFO Frequency in Hz """
        _freq_hz = int(freq)
        self.send_command(f"F {_freq_hz}")


# Connect to Rig and set to initial 'off' frequency.
rig = RIGCTLD()
rig.set_vfo(OFF_TONE)



def midi_callback(event, data=None):
    """ MIDI Event Callback """
    global rig, CW_TONE, OFF_TONE

    # Extract Midi Event Info
    _msg = event[0]

    _channel = _msg[0] & 0xF
    _action = _msg[0] >> 4
    _note = _msg[1]
    _velocity = _msg[2]

    # Currently ignoring all other actions here...
    if _action == 0x8:
        _action = 'NOTE OFF'
    elif _action == 0x9:
        _action = 'NOTE ON'
    else:
        _action = 'UNKNOWN'

    # Calculate Tone frequency
    _freq = int(math.pow(2.0,(_note-69.0)/12.0)*440)

    # Set VFO frequency so beat ends up at the desired frequency,
    # or set to the 'off' frequency.
    if _action == 'NOTE ON':
        rig.set_vfo(CW_TONE-_freq)
    elif _action == 'NOTE OFF':
        rig.set_vfo(OFF_TONE)

    print(f"{_action}: {_freq}")

try:
    midiin, port_name = open_midiinput(args.midi)
except (EOFError, KeyboardInterrupt):
    sys.exit()

midiin.set_callback(midi_callback)

print("Entering main loop. Press Control-C to exit.")
try:
    # Just wait for keyboard interrupt,
    # everything else is handled via the input callback.
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    midiin.close_port()
    del midiin