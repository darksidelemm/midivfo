# MIDI to VFO
A stupid hack to turn a very expensive Amateur Radio into a Monophonic Synth.

Author: Mark Jessop <vk5qi@rfhead.net>

## Dependencies
* Python 3
* python-rtmidi
* Hamlib (in particular rigctld)

## Setup
TODO: Update this to reflect use of direct CI-V control.

* Set a signal generator up on a known frequency (aligned with the rig you are using). In my case I used 14067000 Hz.
* Run up rigctld setup to talk to your radio. In my case I run:
    `rigctld -m 378 -r /dev/tty.SLAB_USBtoUART -s 115200`
* Set radio into Upper-Sideband Mode (USB)

## Operation
(TODO: Clean this all up and update instructions... the below is not quite valid anymore)

* Run up this utility with: `python mifivfo.py --cw 14067000`
* If your midi device is not #0, then set it with --midi
* Play!

## TODO
* 4-Poly?
