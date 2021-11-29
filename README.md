# SN76489AN-MicroPython  
![SN76489 wiring](https://user-images.githubusercontent.com/74131798/143735345-13715234-169d-40fd-b777-f2a5850d6855.png)

MicroPython v1.17+ script for SN76489AN hardware music playback

To import the .VGM files please use Thonny IDE

## Example
```
import machine
import time
import music76489

pwm = machine.PWM(machine.Pin(15))
pwm.freq(3579000)
pwm.duty_u16(32767)

music = music76489.Music76489()

music.load_vgm("boss_battle.vgm")

while True:
    music.tick()
    time.sleep(0.016666)
```

## Authors  
CircuitPython to MicroPython conversion by Kyuchumimo  
CircuitPython script by Ricardo Quesada from quico GitLab Repository  
https://gitlab.com/ricardoquesada/quico/-/blob/master/src/music76489.py  
SN74HC595N MicroPython Library by mcauser  
https://github.com/mcauser/micropython-74hc595
