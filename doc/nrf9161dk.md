# nRF9161DK device guide

## Installation

> **_NOTE_**: If you will be using cellular location or want to speed up GNSS location by using `AGPS`, the development kit needs to be connected to nRF Cloud to get the data. Follow [these steps](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/device_guides/working_with_nrf/nrf91/nrf9160_gs.html#connecting-the-dk-to-nrf-cloud) before installing Micropython on it or while running a MicroPython program that tries
to connect to nRF Cloud (like the Asset Tracker example). This only needs to be done once.

- Download the `nrf9161dk_merged.hex` file from the [firmware directory](/firmware/).
- Download the latest [modem firmware](https://www.nordicsemi.com/Products/nRF9161/Download?lang=en#infotabs). It should be named 
`mfw_nrf9160_2.x.x.zip`. Do NOT unzip the file.
- Install [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-desktop) 
- Use the [Programmer](https://infocenter.nordicsemi.com/topic/ug_nc_programmer/UG/nrf_connect_programmer/ncp_application_overview.html?cp=11_3_2_2) application to program the modem firmware and application Hex file onto your development kit.

## Usage

The interface chip on the nRF9161DK exposes 2 virtual COM ports. The first one is where you will find the MicroPython REPL prompt.

### Filesystem

The first time that you use the device you might need to create the filesystem. You can do that from the REPL prompt:

```python
import os
from zephyr import FlashArea

block_dev = FlashArea(FlashArea.STORAGE, 4096)
os.VfsLfs2.mkfs(block_dev)
os.mount(block_dev, '/flash')
```

### Buttons and LEDs

There are four buttons:
- Button 1: It can be used with `Pin.cpu.gpio0_8`
- Button 2: If pressed at boot time, the board will skip executing a `main.py` file from the filesystem. During normal operation, it can be used with `Pin.cpu.gpio0_9`
- Button 3: It can be used with `Pin.cpu.gpio0_18`
- Button 4: It can be used with `Pin.cpu.gpio0_19`

There are four LEDs:
- LED1: Can be accessed with `Pin.cpu.gpio0_0`
- LED2: Can be accessed with `Pin.cpu.gpio0_1`
- LED3: Can be accessed with `Pin.cpu.gpio0_4`
- LED4: Can be accessed with `Pin.cpu.gpio0_5`


## Pins and GPIO
```python
from machine import Pin

pin = Pin(Pin.cpu.gpio0_2, Pin.OUT)
```
## I2C

The available bus is `i2c2` and this is how you get an instance:
```python
from machine import I2C

i2c = I2C('i2c2')
```
## Cellular Interface

See the [Cellular Guide](/doc/CellularGuide.md) for the network APIs.
