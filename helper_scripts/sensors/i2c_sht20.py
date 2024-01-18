import time
from micropython import const

_TEMP_NO_HOLD   = const(0xF3)
_HUMID_NO_HOLD  = const(0xF5)

# For the following wait values, see Sensirion SH20 datasheet, Table 7
_TEMP_MAX_TIME  = const(85)
_HUMID_MAX_TIME = const(29)

class SHT20:
    def __init__(self, i2c):
        self._i2c = i2c
        self._addr = 0x40   # This is hardwired on the SHT20

    def temperature(self):
        self._i2c.writeto(self._addr, bytes([_TEMP_NO_HOLD]), False) # Don't send a stop
        time.sleep_ms(_TEMP_MAX_TIME)
        data = self._i2c.readfrom(self._addr, 3, True) # Temp data is 3 bytes, send stop
        # TODO: CRC checking

        # Temperature conversion from Sensirion datasheet, section 6.2
        return (data[0] << 8 | data[1]) * 175.72/65536.0 - 46.85

    def humidity(self):
        self._i2c.writeto(self._addr, bytes([_HUMID_NO_HOLD]), False) # Don't send a stop
        time.sleep_ms(_HUMID_MAX_TIME)
        data = self._i2c.readfrom(self._addr, 3, True) # Humid data is 3 bytes, send stop
        # TODO: CRC checking

        # Humidity conversion from Sensirion datasheet, section 6.1
        return (data[0] << 8 | data[1]) * 125.0/65536.0 - 6.0

