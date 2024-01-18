from machine import Pin

BOARD_NAME = "nRF9161DK"

led1 = Pin(Pin.cpu.gpio0_0, Pin.OUT | Pin.IN)
led2 = Pin(Pin.cpu.gpio0_1, Pin.OUT | Pin.IN)
led3 = Pin(Pin.cpu.gpio0_4, Pin.OUT | Pin.IN)
led4 = Pin(Pin.cpu.gpio0_5, Pin.OUT | Pin.IN)

button1 = Pin(Pin.cpu.gpio0_8, Pin.IN, Pin.PULL_UP)
button2 = Pin(Pin.cpu.gpio0_9, Pin.IN, Pin.PULL_UP)
button3 = Pin(Pin.cpu.gpio0_18, Pin.IN, Pin.PULL_UP)
button4 = Pin(Pin.cpu.gpio0_19, Pin.IN, Pin.PULL_UP)

i2c = 'i2c2'
