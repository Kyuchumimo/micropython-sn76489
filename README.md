# MicroPython SN76489
![mp-sn76489-wiring](https://user-images.githubusercontent.com/74131798/214214476-7cec3f70-01a1-4400-947c-a74721a022c5.png)

MicroPython library for SN76489AN + SN74HC595N hardware music playback.

https://www.youtube.com/watch?v=EC8a8s6aKmg

Supports Sega Master System .VGM (v1.50) files from DefleMask Legacy.
To import the .VGM files please use Thonny IDE.

You can use a PWM signal (3584229 Hz, 50% Duty cycle) as a clock signal without any problem.

## Example
```py
import time
import music76489

music = music76489.Music76489()

music.load_vgm("boss_battle.vgm")

try:
    while True:
        delta = time.ticks_us()
        music.tick()
        time.sleep_us(16666-time.ticks_diff(time.ticks_us(), delta))
except KeyboardInterrupt:
    music.reset()
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
