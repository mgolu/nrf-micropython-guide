import network
from umqtt import MQTTClient
import time
import json
from micropython import const
from machine import Pin
from zephyr import console_disable, console_enable, console_is_enabled

# Import the right file for your board here
import nrf9161dk as board
from machine import I2C

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
MQTT_KEEPALIVE = 1200    # in seconds

# Get the following data from your Team ID in nRF Cloud.
TEAM_ID = ""

publish_msg = None

def irq_handler(event, data):
    if event == _IRQ_NW_REG_STATUS:
        # Data is the registration status, same as response to AT+CEREG?
        print(f'Registration status: {str(data)}')
    elif event == _IRQ_RRC_UPDATE:
        # Data is True if connected, False if idle
        print(f'RRC Mode: {"Connected" if data else "Idle"}')
    elif event == _IRQ_CELL_UPDATE:
        global publish_msg
        print(f'Cell update: ID {data[0]}, TAC {data[1]}')
        publish_msg = ('cell_update', data)
    elif event == _IRQ_PSM_UPDATE:
        print(f'PSM parameter update: TAU {data[0]}, Active time {data[1]}')
    elif event == _IRQ_EDRX_UPDATE:
        print(f'eDRX parameter update: Cycle {data[0]}s, PTW {data[1]}s')
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

        msg = f'Location found via {data[0]}: Latitude {data[1]}, Longitude {data[2]}, accuracy {data[3]}'
        if gnss_index > 0:
            msg += f', altitude {data[gnss_index]}, heading {data[gnss_index+1]}, speed {data[gnss_index+2]}'
        print(msg)

        if dt_index > 0:
            print(f'Location found on {data[dt_index]}/{data[dt_index+1]}/{data[dt_index+2]} at {data[dt_index+3]}:{data[dt_index+4]:2d}:{data[dt_index+5]:2d}.{data[dt_index+6]:3d}')
        if (data[0] == "GNSS"):
            global publish_msg
            publish_msg = ('gnss', data)
        elif (data[0] == "Cellular"):
            global publish_msg
            publish_msg = ('cell',)

    elif event == _IRQ_LOCATION_TIMEOUT:
        print("Location timeout")
    elif event == _IRQ_LOCATION_ERROR:
        print("Location error")
    else:
        print("Unknown interrupt: {}".format(event))

def button_publish(p, c, mqtt_device_id):
    if (p == board.button1):
        c.publish(f'prod/{TEAM_ID}/m/d/{mqtt_device_id}/d2c'.encode(), json.dumps({"appId":"BUTTON","messageType":"DATA","data": board.button1.value()}).encode())

def run():
    nic = network.CELL()
    # console_disable(seconds) takes in the number of seconds to disable for. If 0, then it disables
    # indefinitely until console_enable() is called.
    # 
    # Disabling the console (which turns off the UART RX) saves about 1mA
    board.button2.irq(lambda pin: console_disable(0) if console_is_enabled() else console_enable(), trigger=Pin.IRQ_RISING)

    # The following works for Development Kits as they have been provisioned before leaving
    # Nordic's factory with the Device ID: nrf-<imei>
    # https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/device_guides/working_with_nrf/nrf91/nrf9160_gs.html#connecting-the-dk-to-nrf-cloud
    #
    # If the DK has been reprovisioned using the UUID, then change the following line to:
    # mqtt_device_id = nic.status("uuid")
    mqtt_device_id = f'nrf-{nic.status("imei")}'

    nic.irq(handler=irq_handler, mask=_IRQ_NW_REG_STATUS | _IRQ_RRC_UPDATE | _IRQ_CELL_UPDATE | _IRQ_PSM_UPDATE | _IRQ_EDRX_UPDATE 
                |_IRQ_LOCATION_FOUND | _IRQ_LOCATION_TIMEOUT | _IRQ_LOCATION_ERROR)
    nic.connect()
    while not nic.isconnected():
        time.sleep(1)

    time.sleep(1)
    
    # TODO: The following only checks that the driver file is installed. Will need to check
    # if we're able to communicate with the sensor
    try:
        from i2c_sht20 import SHT20
        i2c = I2C(board.i2c)
        sht20 = SHT20(i2c)
    except:
        sht20 = None

    # First try GNSS with low accuracy (fewer satellites), then fallback to cellular.
    while nic.location(gnss=(120,0), cell=20, interval=600) == -16: # -EBUSY
        nic.location_cancel()
        time.sleep(3)

    mqtt_connected = -1
    c = MQTTClient(mqtt_device_id, MQTT_SERVER, ssl=True, ssl_params={'sec_tag': DEFAULT_SEC_TAG})
    board.button1.irq(lambda pin: button_publish(pin, c, mqtt_device_id))

    nic.config(edrx=(81.92,5.12), edrx_enable=True)

    try:
        mqtt_connected = c.connect()

        # First publish the device information that nRF Cloud displays
        c.publish(f'prod/{TEAM_ID}/m/d/{mqtt_device_id}/d2c'.encode(), json.dumps(
                    {'appId':'DEVICE','messageType':'DATA','data': {
                        'deviceInfo': {
                            'board': board.BOARD_NAME,
                            'appName': 'MicroPython Tracker',
                            'appVersion': 'v1.1',
                            'imei': nic.status('imei')
                        },
                        'serviceInfo': {
                            'ui': ['GPS', 'TEMP', 'BUTTON']
                        },
                        'simInfo': {
                            'uiccMode': nic.status('uiccMode'),
                            'iccid': nic.status('iccid'),
                            'imsi': nic.status('imsi')
                        }
                        }
                    }).encode())
    except:
        c.disconnect()

    global publish_msg
    while True:
        time.sleep_ms(1000)
        try:
            if mqtt_connected != 0:
                mqtt_connected = c.connect()
            if publish_msg:
                gnss_index = 0
                if publish_msg[0] == 'gnss':
                    if len(publish_msg[1]) == 7:      # only additional GNSS data
                        gnss_index = 4
                    elif len(publish_msg[1]) == 14:   # Both
                        gnss_index = 11
                    # Publish all the received GNSS data
                    msg = {"appId":"GNSS","messageType":"DATA","data":{"lat":publish_msg[1][1],"lng":publish_msg[1][2],"acc":publish_msg[1][3]}}
                    if gnss_index != 0:
                        msg['data'].update(alt=publish_msg[1][gnss_index], hdg=publish_msg[1][gnss_index+1], spd=publish_msg[1][gnss_index+2])
                    # Now let's add some additional data, it can be any valid key/value pair.
                    # The extra data is not shown on the nRF Cloud portal, but it can be retrieved via REST API
                    msg['data']['extra'] = 80
                    c.publish(f'prod/{TEAM_ID}/m/d/{mqtt_device_id}/d2c'.encode(), json.dumps(msg).encode())
                elif publish_msg[0] == 'cell':
                    # We don't need to publish location because Cell location is saved by nRF Cloud when
                    # the device sends the cell data to nRF Cloud for location information
                    #
                    # This is shown here just in case you want to add something to publish
                    pass
                elif publish_msg[0] == 'cell_update':
                    # We have a new Cell ID, so let's get the latest network status
                    msg = {'appId':'DEVICE','messageType':'DATA','data': {
                        'networkInfo': {
                            'cellID': publish_msg[1][0],
                            'areaCode': publish_msg[1][1],
                            'mccmnc': nic.status('mccmnc'),
                            'currentBand': nic.status('band'),
                            'ipAddress': nic.status('ipAddress'),
                            'networkMode': 'LTE-M' if nic.status('mode') == network.LTE_MODE_LTEM else 'NB-IoT'
                        }
                    }}
                    c.publish(f'prod/{TEAM_ID}/m/d/{mqtt_device_id}/d2c'.encode(), json.dumps(msg).encode())

                # In either case, let's publish temperature and humidity if the sensor is present
                if sht20:
                    msg = {"appId":"TEMP", "messageType": "DATA", "data": sht20.temperature()}
                    c.publish(f'prod/{TEAM_ID}/m/d/{mqtt_device_id}/d2c'.encode(), json.dumps(msg).encode())
                    msg = {"appId":"HUMID", "messageType": "DATA", "data": sht20.humidity()}
                    c.publish(f'prod/{TEAM_ID}/m/d/{mqtt_device_id}/d2c'.encode(), json.dumps(msg).encode())
                publish_msg = None
            
            # This is needed for the MQTT Client to properly handle the keep alive as well
            # as any incoming messages (although this demo doesn't have any incoming messages)
            c.process()
        except:
            c.disconnect()
            mqtt_connected = -1

if __name__ == "__main__":
    run()