# MicroPython experimental support for Nordic devices using Zephyr

This repository has experimental support for MicroPython on Nordic Semiconductor devices running Zephyr.

This support is unofficial, and not supported by Nordic Semiconductor.

## About MicroPython

The main documentation for the MicroPython Zephyr port can be found at the [MicroPython documentation site](https://docs.micropython.org/en/latest/zephyr/quickref.html).

Note that as of this writing (November 2023), the MicroPython Zephyr port uses an older version of Zephyr. This experimental support uses Zephyr v3.4, so there are a few differences, explained here:

### Pins and GPIO

The syntax for getting a Pin instance is different. No better way to explain it than with an example:

    from machine import Pin

    pin = Pin(Pin.cpu.gpio1_6, Pin.OUT)

The constructor for the `Pin` class no longer takes a tuple as the input. Rather, there are pre-defined pins. These can be referenced as pins of the CPU, or as `board` pins if they have a definition.

Look at the device guides for the pins that are available.

## Device Guides

The following boards are currently supported:

* [nRF7002DK](/doc/nRF7002dk.md): BLE and Wi-Fi Development Kit
* [nrf9160DK](/doc/nrf9160dk.md): Cellular and GNSS Development Kit

