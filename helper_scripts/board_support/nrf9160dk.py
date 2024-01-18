from machine import Pin

BOARD_NAME = "nRF9160DK"

led1 = Pin(Pin.cpu.gpio0_2, Pin.OUT | Pin.IN)
led2 = Pin(Pin.cpu.gpio0_3, Pin.OUT | Pin.IN)
led3 = Pin(Pin.cpu.gpio0_4, Pin.OUT | Pin.IN)
led4 = Pin(Pin.cpu.gpio0_5, Pin.OUT | Pin.IN)

button1 = Pin(Pin.cpu.gpio0_6, Pin.IN, Pin.PULL_UP)
button2 = Pin(Pin.cpu.gpio0_7, Pin.IN, Pin.PULL_UP)

i2c = 'i2c1'
