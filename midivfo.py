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
from queue import Queue
from threading import Thread

from rtmidi.midiutil import open_midiinput

from civ import CIV

# Read command-line arguments
parser = argparse.ArgumentParser(description="MIDI to VFO", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--cw", type=int, default=14067000, help="CW Reference Frequency to tune around, in Hz.")
parser.add_argument("--midi", type=int, default=0, help="MIDI Device Number")
args = parser.parse_args()


CW_TONE = args.cw
# Assuming that if we tune above the CW tone that there will be no signal.
# Might not be the case, but that just makes things interesting :-)
OFF_TONE = CW_TONE + 600

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


    def set_freq(self, freq):
        """ Set the main VFO Frequency in Hz """
        _freq_hz = int(freq)
        self.send_command(f"F {_freq_hz}")


class ToneHandler(object):
    """ Polyphony handler """
    def __init__(
        self,
        cw_freq = [14067000],
        tone_callbacks = []
    ):
        self.cw_freq = cw_freq
        self.off_tone = 600
        self.tone_callbacks = tone_callbacks
        self.num_tones = len(self.tone_callbacks)

        self.current_tones = [0] * self.num_tones

        self.last_set = 0

        self.input_queue = Queue()

        self.processing_running = True

        self.processing_thread = Thread(target=self.process_queue)
        self.processing_thread.start()
    

    def close(self):
        self.processing_running = False

    def add_event(self, event, value):
        self.input_queue.put([event, value])

    def process_queue(self):

        print("Input Processing Running")

        while self.processing_running:
            if self.input_queue.qsize() > 0:
                _data = self.input_queue.get()

                _event = _data[0]
                _value = _data[1]

                if _event == 'START':
                    self.start_tone(_value)
                elif _event == 'STOP':
                    self.stop_tone(_value)

        print("Input Processing Stopped")
        

    def set_single(self, index, frequency):
        _freq = self.cw_freq[index] - frequency

        self.tone_callbacks[index](_freq)

    def start_tone(self, frequency):
        
        if frequency in self.current_tones:
            return
        else:
            try:
                ind = self.current_tones.index(0)
                self.current_tones[ind] = frequency
                self.set_single(ind,frequency)
                self.last_set = ind
            except:
                # Can't find a free slot, so, go to the oldest used and set that.
                ind = (self.last_set+1)%self.num_tones
                self.current_tones[ind] = frequency
                self.set_single(ind,frequency)
                self.last_set = ind

        print(self.current_tones)

    def stop_tone(self, frequency):
        if frequency in self.current_tones:
            ind = self.current_tones.index(frequency)
            self.current_tones[ind] = 0
            self.set_single(ind, -600)

        print(self.current_tones)


# Connect to HF Rig (IC-7610) and set to initial 'off' frequency.
hf_rig = CIV()
HF_TONE = CW_TONE
hf_rig.set_a(OFF_TONE)
hf_rig.set_b(OFF_TONE)

# Connect to UHF Rig (IC-9700) and do the same
uhf_rig = CIV(addr=0xA2, port='/dev/tty.SLAB_USBtoUART89')
UHF_TONE = 439399899

# Tone handler setup for just HF rig.
#tone_handler = ToneHandler(cw_freq=[HF_TONE,HF_TONE], tone_callbacks = [rig.set_a, rig.set_b])
# Tone handler setup for just UHF rig (mono)
#tone_handler = ToneHandler(cw_freq=[UHF_TONE], tone_callbacks = [uhf_rig.set_a])

# Two-Rig Setup!
tone_handler = ToneHandler(cw_freq=[HF_TONE,HF_TONE, UHF_TONE], tone_callbacks = [hf_rig.set_a, hf_rig.set_b, uhf_rig.set_a])


def midi_callback(event, data=None):
    """ MIDI Event Callback """
    global tone_handler

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
        _action = f'UNKNOWN: {_action}'

    # Calculate Tone frequency
    _freq = int(math.pow(2.0,(_note-69.0)/12.0)*440)

    # Set VFO frequency so beat ends up at the desired frequency,
    # or set to the 'off' frequency.
    if _action == 'NOTE ON':
        if _velocity > 0:
            tone_handler.add_event('START',_freq)
        else:
            tone_handler.add_event('STOP',_freq)
    elif _action == 'NOTE OFF':
        tone_handler.add_event('STOP',_freq)

    print(f"{_action}: {_freq} {_velocity}")

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