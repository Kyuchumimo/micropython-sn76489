# SN76489AN-MicroPython  
![SN76489 wiring](https://user-images.githubusercontent.com/74131798/154896877-aaa72772-eac4-4006-a067-cae3cc4f58ac.png)

MicroPython v1.17+ library for SN76489AN + SN74HC595N hardware music playback.

Supports Master System .VGM (v1.50) files from DefleMask Legacy.
To import the .VGM files please use Thonny IDE.

You can use a PWM signal (3584229 Hz, 50% Duty cycle) as a clock signal without any problem.

## Example
```
import time
import music76489

music = music76489.Music76489()

music.load_vgm("boss_battle.vgm")

while True:
    delta = time.ticks_us()
    music.tick()
    time.sleep_us(16666-time.ticks_diff(time.ticks_us(), delta))
```

## Known issues
If your music contains periodic noise, the pitch will sound one note up.
This problem is perhaps due to the fact that the SN76489AN chip uses a 15-bit shift register for periodic noise / arbitrary duty cycle instead of 16-bit as in the Sega Master System.

## Authors  
CircuitPython to MicroPython conversion by Kyuchumimo  
CircuitPython script by Ricardo Quesada from quico GitLab Repository  
https://gitlab.com/ricardoquesada/quico/-/blob/master/src/music76489.py  
SN74HC595N MicroPython Library by mcauser  
https://github.com/mcauser/micropython-74hc595
