# Copyright (c) 2021 Ricardo Quesada, Kyuchumimo
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
`quico_music76489`
================================================================================

MicroPython library for playing chiptune music. Intended to work on Raspberry Pi Pico

* Author(s): Ricardo Quesada (CircuitPython), Kyuchumimo (CircuitPython-MicroPython conversion), mcauser (74hc595 Micropython Library)

Implementation Notes
--------------------

Supports VGM format 1.50:
 - https://www.smspower.org/uploads/Music/vgmspec150.txt
 - There are newer VGM formats, but supporting the one used in Deflemask.

**Hardware:**

* Raspberry Pi Pico: https://datasheets.raspberrypi.org/pico/pico-datasheet.pdf

* SN74HC595N 8-Bit Shift Registers:
                  ----U----
  QB Output  01 -|QB    Vcc|- 16  Supply Voltage (3-5V)
  QC Output  02 -|QC     QA|- 15  QA Output
  QD Output  03 -|QD    SER|- 14  Serial Input
  QE Output  04 -|QE     OE|- 13  Output Enable
  QF Output  05 -|QF   RCLK|- 12  Register Clock / Latch
  QG Output  06 -|QG  SRCLK|- 11  Shift Register Clock
  QH Output  07 -|QH  SRCLR|- 10  Shift Register Clear
     Ground  08 -|GND   QH'|- 09  Daisy chain
                  ---------
* SN76489AN Digital Complex Sound Generator:
                         ----U----
  Input Data Bus 2  01 -|D2    Vcc|- 16  Supply Voltage (5V nominally)
  Input Data Bus 1  02 -|D1     D3|- 15  Input Data Bus 3
  Input Data Bus 0  03 -|D0    CLK|- 14  Input Clock
       Ready (OUT)  04 -|READY  D4|- 13  Input Data Bus 4
      Write Enable  05 -|WE     D5|- 12  Input Data Bus 5
       Chip Enable  06 -|CE     D6|- 11  Input Data Bus 6
         Audio Out  07 -|AOUT   D7|- 10  Input Data Bus 7
            Ground  08 -|GND    NC|- 09  No connection
                         ---------

**Software and Dependencies:**

* micropython-74hc595: https://github.com/mcauser/micropython-74hc595

"""

import struct
import utime #K: timer applications for microcontrollers, same as time module

from sr_74hc595_spi import SR #K: adafruit_74hc595 Library Replacement
import machine #K: same or similar as board module
from machine import SPI #K: Serial protocols library, same as busio.SPI class
from machine import Pin #K: Digital input/output library, same as digitalio

# For quick REPL debugging do:
#  import adafruit_74hc595
#  import board
#  import busio
#  import digitalio
#
#  spi = busio.SPI(board.A1, MOSI=board.A2)
#  latch_pin = digitalio.DigitalInOut(board.A3)
#  sr = adafruit_74hc595.ShiftRegister74HC595(spi, latch_pin)
#  we = digitalio.DigitalInOut(board.A4)
#  we.direction = digitalio.Direction.OUTPUT
#  sr.gpio = 0xff

__docformat__ = "restructuredtext"


class Music76489:
    """Class to play music on an SN76489 chip

    For detailed information about the internals of the SN76489 chip, read:
    https://www.smspower.org/Development/SN76489
    """

    def __init__(self):
        self._offset = 0
        self._data = bytearray()
        self._should_loop = False
        self._loop_offset = 0
        self._prev_time = utime.ticks_ms()/1000 #K: same behavior as time.monotonic()
        self._ticks_to_wait = 0
        self._end_of_song = False

        self._spi = SPI(0,sck=Pin(6),mosi=Pin(7)) #K: SPI protocol pin assignment, same as busio.SPI(Clock, MOSI/TX(Optional)=board.pin, MISO/RX(Optional)=board.pin)
        self._latch_pin = Pin(8) #K: Pin A3 digital assignment, same as digitalio.DigitalInOut(board.pin) (rclk)
        self._sr = SR(self._spi, self._latch_pin) #K: adafruit_74hc595 ShiftRegister74HC595 class __init__ Replacement
        self._sn76489_we = Pin(9) #K: Pin A4 digital assignment, same as digitalio.DigitalInOut(board.pin)
        self._sn76489_we = Pin(9, Pin.OUT) #K: Pin A4 digital OUTPUT assignment, same as .direction = digitalio.Direction.OUTPUT

        self._sn76489_we.value(True) #K: same as '.value = True'

        self.reset()

    def load_vgm(self, filename: str) -> None:
        """
        Load a VGM song.

        The loaded song does not play automatically. In order to play the song
        the user must call "tick()" every 1/60s.

        :param str filename: The VGM song to load.
        """
        self.reset()
        with open(filename, "rb") as file:
            # Assuming VGM version is 1.50 (64 bytes of header)
            header = bytearray(file.read(0x40))

            # 0x00: "Vgm " (0x56 0x67 0x6d 0x20) file identification (32 bits)
            if header[:4].decode("utf-8") != "Vgm ":
                raise Exception("Invalid header")

            # 0x08: Version number (32 bits)
            #  Version 1.50 is stored as 0x00000150 (0x50 0x01 0x00 0x00).
            #  This is used for backwards compatibility in players, and defines which
            #  header values are valid.
            vgm_version = struct.unpack_from("<I", header, 8)[0]
            if vgm_version != 0x150:
                raise Exception(
                    f"Invalid VGM version format; got {vgm_version:x}, want 0x150"
                )

            # 0x0c: SN76489 clock (32 bits)
            #  Input clock rate in Hz for the SN76489 PSG chip. A typical value is
            #  3579545. It should be 0 if there is no PSG chip used.
            sn76489_clock = struct.unpack_from("<I", header, 12)[0]
            if sn76489_clock != 3579545:
                raise Exception(
                    f"Invalid VGM clock freq; got {sn76489_clock}, want 3579545"
                )

            # 0x04: Eof offset (32 bits)
            #  Relative offset to end of file (i.e. file length - 4).
            #  This is mainly used to find the next track when concatanating
            #  player stubs and multiple files.
            file_len = struct.unpack_from("<I", header, 4)[0]
            self._data = bytearray(file.read(file_len + 4 - 0x40))

            # 0x1c: Loop offset (32 bits)
            #  Relative offset to loop point, or 0 if no loop.
            #  For example, if the data for the one-off intro to a song was in bytes
            #  0x0040-0x3fff of the file, but the main looping section started at
            #  0x4000, this would contain the value 0x4000-0x1c = 0x00003fe4.
            loop = struct.unpack_from("<I", header, 0x1C)[0]
            self._should_loop = bool(loop != 0)
            self._loop_offset = loop + 0x1C - 0x40

    def tick(self) -> None:
        """
        Play the loaded VGM song.

        Must be called at 1/60s frequency.
        Example:
        m.load_vgm('my_song.vgm')
        while True:
          # game main loop
          # do something
          m.tick()
          time.sleep(1/60)
        """
        if self._end_of_song:
            raise Exception("End of song reached")

        self._ticks_to_wait -= 1
        if self._ticks_to_wait > 0:
            return

        # Convert to local variables (easier to ready... and tiny bit faster?)
        data = self._data
        i = self._offset
        while True:
            if i >= len(data):
                raise Exception(f"unexpected offset: {i} >= {len(data)}")

            # Valid commands
            #  0x4f dd    : Game Gear PSG stereo, write dd to port 0x06
            #  0x50 dd    : PSG (SN76489/SN76496) write value dd
            #  0x51 aa dd : YM2413, write value dd to register aa
            #  0x52 aa dd : YM2612 port 0, write value dd to register aa
            #  0x53 aa dd : YM2612 port 1, write value dd to register aa
            #  0x54 aa dd : YM2151, write value dd to register aa
            #  0x61 nn nn : Wait n samples, n can range from 0 to 65535 (approx 1.49
            #               seconds). Longer pauses than this are represented by multiple
            #               wait commands.
            #  0x62       : wait 735 samples (60th of a second), a shortcut for
            #               0x61 0xdf 0x02
            #  0x63       : wait 882 samples (50th of a second), a shortcut for
            #               0x61 0x72 0x03
            #  0x66       : end of sound data
            #  0x67 ...   : data block: see below
            #  0x7n       : wait n+1 samples, n can range from 0 to 15.
            #  0x8n       : YM2612 port 0 address 2A write from the data bank, then wait
            #               n samples; n can range from 0 to 15. Note that the wait is n,
            #               NOT n+1.
            #  0xe0 dddddddd : seek to offset dddddddd (Intel byte order) in PCM data bank

            # print(f'data: 0x{data[i]:02x}')

            #  0x50 dd    : PSG (SN76489/SN76496) write value dd
            if data[i] == 0x50:
                self._write_port_data(data[i + 1])
                i = i + 2

            #  0x61 nn nn : Wait n samples, n can range from 0 to 65535 (approx 1.49
            #               seconds). Longer pauses than this are represented by multiple
            #               wait commands.
            elif data[i] == 0x61:
                # unpack little endian unsigned short
                delay = struct.unpack_from("<H", data, i + 1)[0]
                self._delay_n(delay)
                i = i + 3
                break

            #  0x62       : wait 735 samples (60th of a second), a shortcut for
            #               0x61 0xdf 0x02
            elif data[i] == 0x62:
                self._delay_one()
                i = i + 1
                break

            #  0x66       : end of sound data
            elif data[i] == 0x66:
                if self._should_loop:
                    i = self._loop_offset
                else:
                    self._end_of_song = True
                    break

            else:
                raise Exception("Unknown value: data[0x%x] = 0x%x" % (i, data[i]))
        # update offset
        self._offset = i

    def _delay_one(self) -> None:
        self._ticks_to_wait += 1

    def _delay_n(self, samples: int) -> None:
        # 735 samples == 1/60s
        self._ticks_to_wait += samples // 735

    def play_vgm(self, filename: str) -> None:
        """
        Play a VGM song file.

        This is a "sync" function, meaning that it will return only after the
        music ends playing.

        :param str filename: The VGM file to play.
        """
        self.load_vgm(filename)
        while not self._end_of_song:
            self.tick()
            # One tick == 1/60 of a second
            utime.sleep(1 / 60)

    def play_freq(self, channel: int, freq: float) -> None:
        """
        Play a certain frequency.

        :param int channel: One of the 3 available channels:0, 1 or 2.
        :param float freq: Frequency to play. Valid range: 110.35 - 55930.4
        """
        # Supported frequency range: [110.35 - 55930.4]
        # Although freqs > 7902.13 shouldn't be used
        # In terms of musical notes the range is: [A2 - B8+]
        # Formula taken from here: https://www.smspower.org/Development/SN76489
        clock = 3579545  # Hz
        reg = int(clock // (freq * 2 * 16))

        # 1022 and 1023 are reserved for samples
        if reg > 1021:
            reg = 1021

        lsb = reg & 15
        msb = reg >> 4

        # Latch + tone
        # bit7: 1=Latch
        # bit4: 0=Tone
        data = 0b1000_0000
        # Channel: Bits 5,6
        data |= channel << 5
        # tone lsb: Bits 0-3
        data |= lsb
        self._write_port_data(data)

        # Data
        # bit7: 0=Data
        data = 0b0000_0000
        # tone msb: Bits 0-5
        data |= msb
        self._write_port_data(data)

    def _play_note(self, voice: int, note: int, octave: int) -> None:
        # Initial note C0:
        # https://pages.mtu.edu/~suits/notefreqs.html
        note_c0 = 16.35
        distance = octave * 12 + note
        freq = note_c0 * (2 ** (distance / 12))
        self.play_freq(voice, freq)

    def play_notes(self, notes: str) -> None:
        """
        Play music notes.

        Supported values are:

        Notes: C, C#, D, D#, E, F, F#, G, G#, A, A#, B
        Voice: Vn, where n is:0, 1 or 2
        Octave: On, where n is: 0-9
        Volume: Un, where n is: 0-9
        Note duration: W, H, Q, I or S
         W: Whole,
         H: Half,
         Q: Quarter
         I: Eighth
         S: Sixteenth

        Example: TODO

        :param str notes: Notes to play.
        """
        # Inspired by C128 "play" BASIC command:
        # https://www.commodore.ca/manuals/128_system_guide/sect-07b.htm#7.3.html

        # Defaults
        voice = 0
        octave = 4
        duration = 16

        # Hack
        notes = notes + " "

        i = 0
        while i < len(notes):
            n = notes[i]
            if n == "V":
                # Voice: voices go from 0-2
                voice = notes[i + 1]
                i += 2
            elif n == "O":
                octave = int(notes[i + 1])
                i += 2
            elif n in "CDEFGAB":
                # Notes that belong to the chromatic scale:
                # C, C#, D, D#, E, F, F#, G, G#, A, A#, B
                chromatic = {
                    "C": 0,
                    "C#": 1,
                    "D": 2,
                    "D#": 3,
                    "E": 4,
                    "F": 5,
                    "F#": 6,
                    "G": 7,
                    "G#": 8,
                    "A": 9,
                    "A#": 10,
                    "B": 11,
                }
                if notes[i + 1] == "#":
                    n = n + "#"
                    i += 1
                note = chromatic[n]
                self.set_vol(voice, 9)
                self._play_note(voice, note, octave)
                i += 1
                # TODO: support envelops
                utime.sleep(0.016666 * duration * 2)
                self.set_vol(voice, 0)
                utime.sleep(0.016666)

            elif n == "U":
                # TODO: Remove volument support in favor of envelops
                # Volume
                vol = int(notes[i + 1])
                self.set_vol(voice, vol)
                i += 2
            elif n in "WHQIS":
                dur_dict = {
                    "W": 64,  # Whole
                    "H": 32,  # Half
                    "Q": 16,  # Quarter
                    "I": 8,  # Eighth
                    "S": 4,  # Sixteenth
                }
                duration = dur_dict[n]
                i += 1
            elif n in " ,":
                i += 1
        self.set_vol(0, 0)

    def play_noise(self, mode: int, shift_rate: int) -> None:
        """
        Play noise in channel 3.

        :param int mode: Supported modes: 0==periodic noise, 1==white noise
        :param shift_rate int: Shift rate to used according to the SN76489 specification.
        """
        assert mode in (0, 1)
        assert 0 <= shift_rate <= 3

        # Latch + noise
        # bit7: 1=latch
        # bit 5,6: 11=channel 3 (noise)
        # bit4: 1=noise/tone (not vol)
        data = 0b1111_0000
        # mode: white=1, periodic=0
        data |= mode << 2
        data |= shift_rate
        self._write_port_data(data)

    def set_vol(self, channel: int, vol: int) -> None:
        """
        Set the volume for the given channel.

        :param int channel: Channel to be used. Valid values: 0-3.
        :param int vol: Volume to set. Values:0-15, where 0 is silence and 15 max volume.
        """
        assert 0 <= channel <= 3
        assert 0 <= vol <= 15

        # Latch + Volume
        # bit7: 1=latch
        # bit4: 1=volumen
        data = 0b1001_0000
        # Channel
        data |= channel << 5
        # Volume
        data |= 15 - vol
        self._write_port_data(data)

    def _write_port_data(self, byte_data) -> None:
        # Send data
        self._sr[0] = byte_data #K: sr.gpio replacement

        # Enable SN76489
        self._sn76489_we.value(False) #K: same as '.value = False'
        # Allow it to read, and wait a very small time (needed?)
        # time.sleep(0.001)
        # Disable SN76489
        self._sn76489_we.value(True) #K: same as '.value = True'

    def reset(self) -> None:
        """
        Reset the SN76489 chip.

        Set volume to 0 in all channels.
        """
        reset_seq = [0x9F, 0xBF, 0xDF, 0xFF]
        for b in reset_seq:
            self._write_port_data(b)
        self._offset = 0
        self._data = bytearray()
