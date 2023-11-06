
from micropython import const
import struct
import bluetooth
import time


_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)

_IO_CAPABILITY_DISPLAY_ONLY = const(0)
_IO_CAPABILITY_DISPLAY_YESNO = const(1)
_IO_CAPABILITY_KEYBOARD_ONLY = const(2)
_IO_CAPABILITY_NO_INPUT_OUTPUT = const(3)
_IO_CAPABILITY_KEYBOARD_DISPLAY = const(4)

# Generate a payload to be passed to gap_advertise(adv_data=...).
def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value

    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )

    if name:
        _append(_ADV_TYPE_NAME, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # See org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

    return payload

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

_INFORMATION = (
    bluetooth.UUID("14387801-130c-49e7-b877-2881c89cb258"),
    _FLAG_READ,
)

_CONTROL_POINT = (
    bluetooth.UUID("14387802-130c-49e7-b877-2881c89cb258"),
    _FLAG_WRITE | _FLAG_INDICATE,
    (
        (
            # org.bluetooth.descriptor.gatt.characteristic_user_description
            bluetooth.UUID(0x2901),
            _FLAG_READ | _FLAG_WRITE,
        ),
    ),
)

_DATA_OUT = (
    bluetooth.UUID("14387803-130c-49e7-b877-2881c89cb258"),
    _FLAG_NOTIFY,
    (
        (
            # org.bluetooth.descriptor.gatt.characteristic_user_description
            bluetooth.UUID(0x2901),
            _FLAG_READ | _FLAG_WRITE,
        ),
    ),
)

_PROV_SERVICE = (
    bluetooth.UUID("14387800-130c-49e7-b877-2881c89cb258"),
    ( _INFORMATION, _CONTROL_POINT, _DATA_OUT ),
)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_CONNECTION_UPDATE = const(27)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_PASSKEY_ACTION = const(31)

_PASSKEY_ACTION_NONE = const(0)
_PASSKEY_ACTION_INPUT = const(2)
_PASSKEY_ACTION_DISPLAY = const(3)
_PASSKEY_ACTION_NUMERIC_COMPARISON = const(4)

class BLEProvisioningService:
    def __init__(self, ble):
        self._scan_response = bytearray()
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._ble.config(io=_IO_CAPABILITY_DISPLAY_YESNO, mitm=False, bond=False)
        self.passkey_handle = None
        self.connections = []
        self.addresses = []
        print(self._ble.gatts_register_services((_PROV_SERVICE,)))
        #((self._handle_info, self._handle_control, self._handle_data),) = self._ble.gatts_register_services((_PROV_SERVICE,))
        self._scan_response += struct.pack("BB", 21, 0x21) + _PROV_SERVICE[0] + struct.pack("BBBB", 0, 0, 0, 0)
        self._advertise()
    
    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            self.connections.append(conn_handle)
            self.addresses.append(addr)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            self.connections.remove(conn_handle)
            self.addresses.remove(addr)
            self._advertise()
        elif event == _IRQ_GATTS_INDICATE_DONE:
            print("Indicate done")
        elif event == _IRQ_PASSKEY_ACTION:
            self.passkey_handle, self.passkey_action, self.passkey = data
        elif event == _IRQ_ENCRYPTION_UPDATE:
            print("Encryption update")


    def _advertise(self, interval_us=100000):
        self._scan_response[19] = 7
        self._ble.gap_advertise(interval_us, adv_data=advertising_payload(name="mpy", services=[_PROV_SERVICE[0]]), resp_data=self._scan_response)
        print("Start advertising")

    def write(self, handle, data):
        self._ble.gatts_write(handle, data)

def run():
    ble = bluetooth.BLE()
    p = BLEProvisioningService(ble)
    try:
        while True:
            if p.passkey_handle is not None:
                if p.passkey_action == _PASSKEY_ACTION_NONE:
                    print("Passkey action none")
                elif p.passkey_action == _PASSKEY_ACTION_INPUT:
                    print("Passkey action input")
                    p._ble.gap_passkey(p.passkey_handle, _PASSKEY_ACTION_INPUT, 0)
                elif p.passkey_action == _PASSKEY_ACTION_DISPLAY:
                    print("Passkey display: {:06}".format(p.passkey))
                elif p.passkey_action == _PASSKEY_ACTION_NUMERIC_COMPARISON:
                    print("Passkey: {:06}. Press button 1 if match, 2 if not".format(p.passkey))
                    time.sleep(3)
                    p._ble.gap_passkey(p.passkey_handle, _PASSKEY_ACTION_NUMERIC_COMPARISON, 1)
                else:
                    print("Other action")
                p.passkey_handle = None
            time.sleep_ms(100)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
   