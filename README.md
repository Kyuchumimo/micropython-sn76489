# SN76489AN-MicroPython  
![SN76489 wiring](https://user-images.githubusercontent.com/74131798/145133756-7b034919-eb7a-4d20-a082-c95bad3793f7.png)

MicroPython v1.17+ library for SN76489AN + SN74HC595N hardware music playback.

Supports Master System/Game Gear .VGM (v1.50) files from DefleMask Legacy.
To import the .VGM files please use Thonny IDE.

You can use a PWM signal as a clock signal without any problem.

## Example
```
import time
import music76489

music = music76489.Music76489()

music.load_vgm("boss_battle.vgm")

while True:
    music.tick()
    time.sleep(0.016)
```

## Authors  
CircuitPython to MicroPython conversion by Kyuchumimo  
CircuitPython script by Ricardo Quesada from quico GitLab Repository  
https://gitlab.com/ricardoquesada/quico/-/blob/master/src/music76489.py  
SN74HC595N MicroPython Library by mcauser  
https://github.com/mcauser/micropython-74hc595
