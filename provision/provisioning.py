
from micropython import const
import struct
import bluetooth
import time
import minipb


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
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_CONNECTION_UPDATE = const(27)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_PASSKEY_ACTION = const(31)

_PASSKEY_ACTION_NONE = const(0)

ADV_DATA_VERSION_IDX = 18

@minipb.process_message_fields
class ScanParams(minipb.Message):
    band =          minipb.Field(1, minipb.TYPE_UINT)
    passive =       minipb.Field(2, minipb.TYPE_BOOL)
    period_ms =     minipb.Field(3, minipb.TYPE_UINT)
    group_channels = minipb.Field(4, minipb.TYPE_UINT)

@minipb.process_message_fields
class Request(minipb.Message):
    op_code =       minipb.Field(1, minipb.TYPE_UINT)
    scan_params =   minipb.Field(10, ScanParams)

@minipb.process_message_fields
class WifiInfo(minipb.Message):
    ssid =          minipb.Field(1, minipb.TYPE_BYTES, required=True)
    bssid =         minipb.Field(2, minipb.TYPE_BYTES, required=True)
    band =          minipb.Field(3, minipb.TYPE_UINT)
    channel =       minipb.Field(4, minipb.TYPE_UINT32, required=True)
    auth =          minipb.Field(5, minipb.TYPE_UINT)

@minipb.process_message_fields
class ConnectionInfo(minipb.Message):
    ip4_addr = minipb.Field(1, minipb.TYPE_BYTES)

@minipb.process_message_fields
class DeviceStatus(minipb.Message):
    state =         minipb.Field(1, minipb.TYPE_UINT)
    provioning_info = minipb.Field(10, WifiInfo)
    connection_info = minipb.Field(11, ConnectionInfo)
    scan_info =     minipb.Field(12, ScanParams)

@minipb.process_message_fields
class Response(minipb.Message):
    op_code =       minipb.Field(1, minipb.TYPE_UINT)
    status =        minipb.Field(2, minipb.TYPE_UINT)
    device_status = minipb.Field(10, DeviceStatus)

class BLEProvisioningService:
    def __init__(self, ble):
        self._scan_response = bytearray()
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._ble.config(io=_IO_CAPABILITY_NO_INPUT_OUTPUT, mitm=False, bond=False)
        self.passkey_handle = None
        self.connections = []
        self.addresses = []
        self.writes = []
        #print(self._ble.gatts_register_services((_PROV_SERVICE,)))
        ((self._handle_info, self._handle_control, cud0, self._handle_data, cud1),) = self._ble.gatts_register_services((_PROV_SERVICE,))
        version_msg = minipb.Wire([('version', 'T')])
        self._ble.gatts_write(self._handle_info, version_msg.encode({'version': 0x01})) # set the version
        self._scan_response += struct.pack("BB", 21, 0x21) + _PROV_SERVICE[0] + struct.pack("BBBB", 1, 0, 0, 0)
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
        elif event == _IRQ_GATTS_WRITE:
            handle, attr = data
            self.writes.insert(0, (handle, attr))


    def _advertise(self, interval_us=100000):
        self._scan_response[ADV_DATA_VERSION_IDX] = 1
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
                else:
                    print("Other action")
                p.passkey_handle = None
            while p.writes:
                w = p.writes.pop()
                req = Request.decode(p._ble.gatts_read(w[1]))
                print(req)
                if req.op_code == 1: # GET_STATUS
                    print("Get Status Received")
                    rsp = Response()
                    rsp.status = 0 # SUCCESS
                    rsp.op_code = req.op_code
                    stat = DeviceStatus(state=0) # DISCONNECTED
                    rsp.device_status = stat 
                    p._ble.gatts_indicate(w[0], w[1], rsp.encode())
            time.sleep_ms(100)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
    