# SN76489AN-MicroPython  
![SN76489 wiring](https://user-images.githubusercontent.com/74131798/151239402-02b0c4a8-b04e-4b2f-be5f-0f5a4f2403dd.png)

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

## Authors  
CircuitPython to MicroPython conversion by Kyuchumimo  
CircuitPython script by Ricardo Quesada from quico GitLab Repository  
https://gitlab.com/ricardoquesada/quico/-/blob/master/src/music76489.py  
SN74HC595N MicroPython Library by mcauser  
https://github.com/mcauser/micropython-74hc595
