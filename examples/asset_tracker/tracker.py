import network
from umqtt import MQTTClient
import time
from micropython import const
import nrf9160dk as board

_IRQ_NW_REG_STATUS       = const(0x1)
_IRQ_PSM_UPDATE          = const(0x2)
_IRQ_EDRX_UPDATE         = const(0x4)
_IRQ_RRC_UPDATE          = const(0x8)
_IRQ_CELL_UPDATE         = const(0x10)
_IRQ_LTE_MODE_UPDATE     = const(0x20)
_IRQ_TAU_PRE_WARN        = const(0x40)
_IRQ_NEIGHBOR_CELL_MEAS  = const(0x80)
_IRQ_LOCATION_FOUND      = const(0x100)
_IRQ_LOCATION_TIMEOUT    = const(0x200)
_IRQ_LOCATION_ERROR      = const(0x400)

DEFAULT_SEC_TAG = const(16842753)  # nRF Cloud default sec_tag
CA_CERT_TYPE = const(0)
MQTT_SERVER = "mqtt.nrfcloud.com"
# Get the following data from your Team ID in nRF Cloud. Prefix is prod/<teamID>
MQTT_PREFIX = b"prod/<team-id>"
CLIENT_ID = "<device-id>"
MQTT_PUB_TOPIC = b"m/d/<device-id>/d2c"

publish_gnss = None

def irq_handler(event, data):
    if event == _IRQ_NW_REG_STATUS:
        # Data is the registration status, same as response to AT+CEREG?
        print("Registration status: " + str(data))
    elif event == _IRQ_RRC_UPDATE:
        # Data is True if connected, False if disconnected
        print("RRC Mode: {}".format("Connected" if data else "Disconnected"))
    elif event == _IRQ_PSM_UPDATE:
        print("PSM parameter update: TAU {}, Active time {}".format(data[0], data[1]))
    elif event == _IRQ_LOCATION_FOUND:
        dt_index = 0        # Index in the data tuple where to find datetime. If there is no datetime, then stays at 0
        gnss_index = 0      # Index in the data tuple where to find additional GNSS data. If 0, there is no data

        if len(data) == 7:      # only additional GNSS data
            gnss_index = 4
        elif len(data) == 11:   # only datetime data
            dt_index = 4
        elif len(data) == 14:   # Both
            dt_index = 4
            gnss_index = 11

        msg = "Location found via {}: Latitude {}, Longitude {}, accuracy {}".format(data[0], data[1], data[2], data[3])
        if gnss_index > 0:
            msg += ", altitude {}, heading {}, speed {}".format(data[gnss_index], data[gnss_index+1], data[gnss_index+2])
        print(msg)

        if dt_index > 0:
            print("Location found on {}/{}/{} at {}:{:2d}:{:2d}.{:3d}".format(data[dt_index], data[dt_index+1], data[dt_index+2], data[dt_index+3], data[dt_index+4], data[dt_index+5], data[dt_index+6]))
        if (data[0] == "GNSS"):
            global publish_gnss
            publish_gnss = data

    elif event == _IRQ_LOCATION_TIMEOUT:
        print("Location timeout")
    elif event == _IRQ_LOCATION_ERROR:
        print("Location error")
    else:
        print("Unknown interrupt: {}".format(event))

def button_press(p, c):
    if (p == board.button1 and board.button1.value() == 0):
        c.publish(MQTT_PREFIX + MQTT_PUB_TOPIC, b'{"appId":"BUTTON","messageType":"DATA","data":"0"}')
    elif (p == board.button2 and board.button2.value() == 0):
        c.publish(MQTT_PREFIX + MQTT_PUB_TOPIC, b'{"appId":"BUTTON","messageType":"DATA","data":"1"}')

def run():
    global publish_gnss
    nic = network.CELL()
    nic.active(True)
    nic.irq(handler=irq_handler, mask=_IRQ_NW_REG_STATUS | _IRQ_RRC_UPDATE | _IRQ_PSM_UPDATE | _IRQ_LOCATION_FOUND | _IRQ_LOCATION_TIMEOUT | _IRQ_LOCATION_ERROR)
    nic.connect()
    while not nic.isconnected():
        time.sleep(1)

    time.sleep(1)
    # First try GNSS with low accuracy (fewer satellites), then fallback to cellular.
    nic.location(gnss=(120,0), cell=20, interval=300)
    #nic.location(cell=20)

    try:
        c = MQTTClient(CLIENT_ID, MQTT_SERVER, ssl=True, ssl_params={'sec_tag': DEFAULT_SEC_TAG})
        c.connect()

        board.button1.irq(lambda pin: button_press(pin, c))
        board.button2.irq(lambda pin: button_press(pin, c))

        while True:
            time.sleep_ms(1000)
            if publish_gnss:
                gnss_index = 0
                if len(publish_gnss) == 7:      # only additional GNSS data
                    gnss_index = 4
                elif len(publish_gnss) == 14:   # Both
                    gnss_index = 11
                if gnss_index == 0:
                    msg = "".join(['{"appId":"GNSS","messageType":"DATA","data":{"lat":', str(publish_gnss[1]),',"lng":', str(publish_gnss[2]),',"acc":',str(publish_gnss[3]),'}}'])
                else:
                    msg = "".join(['{"appId":"GNSS","messageType":"DATA","data":{"lat":', str(publish_gnss[1]),',"lng":', str(publish_gnss[2]),',"acc":',str(publish_gnss[3]),
                                    ',"alt":',str(publish_gnss[gnss_index]),',"hdg":',str(publish_gnss[gnss_index+1]),',"spd":',str(publish_gnss[gnss_index+2]),'}}'])
                c.publish(MQTT_PREFIX + MQTT_PUB_TOPIC, str.encode(msg))
                publish_gnss = None
    finally:
        c.disconnect()

'''
{
    "appId": "GNSS",
    "messageType": "DATA",
    "data": {
        "lng": 10.438480546503483,
        "lat": 63.421606473153552,
        "acc": 15.699377059936523,
        "alt": 159.65350341796875,
        "spd": 0.064503081142902374,
        "hdg": 0,
        "bat": 77,
        "foo": "bar",
        "extra": "property"
    }
}
'''
    

if __name__ == "__main__":
    run()