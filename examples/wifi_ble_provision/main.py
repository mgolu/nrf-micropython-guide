import provisioning
from machine import Pin

provisioning.run(led = Pin(Pin.cpu.gpio1_6, Pin.OUT))