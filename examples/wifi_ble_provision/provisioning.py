
from micropython import const
from machine import Pin
import struct
import bluetooth
import network
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
_IRQ_PASSKEY_ACTION = const(31)

_PASSKEY_ACTION_NONE = const(0)

_IRQ_STA_CONNECT = const(1)
_IRQ_STA_DISCONNECT = const(2)

ADV_DATA_VERSION_IDX = 18

@minipb.process_message_fields
class ScanParams(minipb.Message):
    band =          minipb.Field(1, minipb.TYPE_UINT)
    passive =       minipb.Field(2, minipb.TYPE_BOOL)
    period_ms =     minipb.Field(3, minipb.TYPE_UINT)
    group_channels = minipb.Field(4, minipb.TYPE_UINT)

@minipb.process_message_fields
class WifiInfo(minipb.Message):
    ssid =          minipb.Field(1, minipb.TYPE_BYTES, required=True)
    bssid =         minipb.Field(2, minipb.TYPE_BYTES, required=True)
    band =          minipb.Field(3, minipb.TYPE_UINT)
    channel =       minipb.Field(4, minipb.TYPE_UINT, required=True)
    auth =          minipb.Field(5, minipb.TYPE_UINT)

@minipb.process_message_fields
class WifiConfig(minipb.Message):
    wifi =          minipb.Field(1, WifiInfo)
    passphrase =    minipb.Field(2, minipb.TYPE_BYTES)
    volatileMemory = minipb.Field(3, minipb.TYPE_BOOL)

@minipb.process_message_fields
class Request(minipb.Message):
    op_code =       minipb.Field(1, minipb.TYPE_UINT)
    scan_params =   minipb.Field(10, ScanParams)
    config =        minipb.Field(11, WifiConfig)

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

@minipb.process_message_fields
class ScanRecord(minipb.Message):
    wifi =  minipb.Field(1, minipb.TYPE_BYTES) # maximum recursion issue
    rssi =  minipb.Field(2, minipb.TYPE_INT)

@minipb.process_message_fields
class Result(minipb.Message):
    scan_record =   minipb.Field(1, ScanRecord)
    state =         minipb.Field(2, minipb.TYPE_UINT)
    reason =        minipb.Field(3, minipb.TYPE_UINT)

class CredentialConnector:
    def __init__(self, nic):
        self._nic = nic
        self._nic.irq(self._nic_irq)
        self._connecting = False
    
    def _nic_irq(self, event, data):
        if event == _IRQ_STA_CONNECT:
            # data[0] will be 0 if successful, an error code otherwise
            self.connection_status = data[0]
            if self._cb:
                self._cb(data[0])
            self._connecting = False

    def connect_nonblocking(self, ssid, cb, timeout=10):
        self._cb = cb
        self._connecting = True
        self._nic.credential('connect', ssid, timeout)

    def connect_blocking(self, ssid, timeout=10):
        self.connect_nonblocking(ssid, None, timeout)
        while self._connecting:
            time.sleep_ms(200)
        return self.connection_status

    def connect_any(self):
        """Start connecting to stored credentials

        This will attempt to connect to all the stored credentials, one by one.
        It will stop when it successfully connects to a Wi-Fi access point. It
        will not start if already connected, so call nic.disconnect() first if
        needed.
        """

        for profile in self._nic.credential('list'):
            if not self._nic.isconnected():
                self.connect_blocking(profile[0])
 
class BLEProvisioningService:
    def __init__(self, ble, nic):
        self._scan_response = bytearray()
        self._nic = nic
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self.passkey_handle = None
        self.connections = []
        self.addresses = []
        self.request = None
        ((self._handle_info, self._handle_control, _, self._handle_data, _),) = self._ble.gatts_register_services((_PROV_SERVICE,))
        version_msg = minipb.Wire([('version', 'T')])
        self._ble.gatts_write(self._handle_info, version_msg.encode({'version': 0x01})) # set the version
        self._ble.gatts_set_buffer(self._handle_control, 150)
    
    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            self.connections.append(conn_handle)
            self.addresses.append(addr)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            self.connections.remove(conn_handle)
            self.addresses.remove(addr)
        elif event == _IRQ_PASSKEY_ACTION:
            self.passkey_handle, self.passkey_action, self.passkey = data
        elif event == _IRQ_GATTS_WRITE:
            handle, attr = data
            if (attr == self._handle_control):
                self.request = handle

    def _notify_connection(self, status):
        res = Result()
        res.state = 4 if (status == 0) else 5 # CONNECTED or CONNECTION_FAILED
        self._ble.gatts_write(self._handle_data, res.encode(), True)

    def advertise(self, interval_us=1000000):
        self._scan_response += struct.pack("BB", 21, 0x21) + _PROV_SERVICE[0] + struct.pack("BBBB", 1, 0, 0, 0)
        self._ble.gap_advertise(interval_us, adv_data=advertising_payload(name="mpy", services=[_PROV_SERVICE[0]]), resp_data=self._scan_response)
    
    def end(self):
        self._ble.gap_advertise(None)

    def handle_request(self):
        rsp = Response()
        data = self._ble.gatts_read(self._handle_control)
        # We could call Request.decode(data), but the nested Messages take
        # quite a bit of RAM, so let's get a raw Wire, and get the inside
        # Messages separately
        raw = minipb.Wire.decode_raw(data)
        rsp.op_code = raw[0]['data']

        if rsp.op_code == 1: # GET_STATUS
            try:
                status = self._nic.status()
                if status == network.STAT_GOT_IP:
                    rsp.device_status = DeviceStatus(state=4)
                elif status == network.STAT_CONNECTING:
                    rsp.device_status = DeviceStatus(state=3)
                else:
                    rsp.device_status = DeviceStatus(state=0)
                profiles = self._nic.credential('list')
                if len(profiles) > 0:
                    #for profile in profiles: 
                    # Current provisioning App only supports 1 profile
                    profile = profiles[len(profiles) - 1]
                    info = WifiInfo()
                    info.ssid = profile[0]
                    info.bssid = profile[1]
                    info.auth = profile[2]
                    info.channel = 255  # WIFI_CHANNEL_ANY

                rsp.status = 0 # SUCCESS
            except:
                rsp.status = 3 # INTERNAL_ERROR
        elif rsp.op_code == 2: # START_SCAN
            try:
                scans = self._nic.scan()
                for scan in scans:
                    ap = Result()
                    ap.scan_record = ScanRecord()
                    ap.scan_record.rssi = abs(scan[3]) # TODO: figure out why minipb doesn't take negative values
                    wifi = WifiInfo()
                    wifi.ssid = scan[0]
                    wifi.bssid = scan[1]
                    wifi.channel = scan[2]
                    wifi.auth = scan[4]
                    ap.scan_record.wifi = wifi.encode()
                    self._ble.gatts_notify(self.request, self._handle_data, ap.encode())
                rsp.status = 0
            except:
                rsp.status = 3
        elif rsp.op_code == 3: # STOP_SCAN
            # There is no API to stop scanning, so just return success
            rsp.status = 0
        elif rsp.op_code == 4: # SET_CONFIG
            rsp.op_code = 4
            config = WifiConfig.decode(raw[1]['data'])
            ssid = config.wifi.ssid
            if len(ssid) == 0:
                # We need an SSID for Certificate Storage
                rsp.status = 3
            else:
                # TODO: Add other restrictions (like Band)
                self._nic.credential('add', ssid=ssid, auth=config.wifi.auth, key=config.passphrase)
                #bssid = config.wifi.bssid # We'll discard this, so we can connect to any AP with the SSID
                cc = CredentialConnector(self._nic)
                cc.connect_nonblocking(ssid, self._notify_connection)
                rsp.status = 0

        self._ble.gatts_indicate(self.request, self._handle_control, rsp.encode())
        self.request = None           

def run(terminateOnConnected=True, led=None):
    nic = network.WLAN(network.STA_IF)
    if nic.isconnected():   # The App only handles one connection, so don't start if we're already connected
        return
    ble = bluetooth.BLE()
    
    # Pairing is required, so we need to set the input/output capabilities of the device.
    # This can be changed if a device has a keyboard or display, but for now pairing will
    # be Just Works.
    ble.config(io=_IO_CAPABILITY_NO_INPUT_OUTPUT, mitm=False, bond=False)
    p = BLEProvisioningService(ble, nic)
    p.advertise()
    loops = 0
    try:
        # This is the main loop for the application, as most everything else
        # runs on a callback/interrupt way.
        while True:
            # If using anything other than Just Works pairing, would have to
            # handle the pairing events here
            if p.passkey_handle is not None:
                if p.passkey_action == _PASSKEY_ACTION_NONE:
                    print("Passkey action none")
                else:
                    print("Other action")
                p.passkey_handle = None
            
            # These are the requests coming over BLE by the provisioning App.
            if p.request is not None:
                p.handle_request()
            if terminateOnConnected and nic.isconnected():
                break

            if led != None:
                loops += 1
                if p.connections:
                    led.value(1)
                elif (loops % 5) == 0: # Flash every 500ms
                    led.value(0 if (loops % 10) == 0 else 1)
            time.sleep_ms(100)
    except KeyboardInterrupt:
        pass
    p.end()
    led.value(0)


if __name__ == "__main__":
    run(led = Pin(Pin.cpu.gpio1_6, Pin.OUT))
    