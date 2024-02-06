import network
import time
from nrfcloud_mqtt import nRFCloudMQTT
from micropython import const
from collections import deque
from machine import Pin
from zephyr import console_disable, console_enable, console_is_enabled

# Import the right file for your board here
import nrf9161dk as board
from machine import I2C

_IRQ_NW_REG_STATUS              = const(0x1)
_IRQ_PSM_UPDATE                 = const(0x2)
_IRQ_EDRX_UPDATE                = const(0x4)
_IRQ_RRC_UPDATE                 = const(0x8)
_IRQ_CELL_UPDATE                = const(0x10)
_IRQ_LTE_MODE_UPDATE            = const(0x20)
_IRQ_TAU_PRE_WARN               = const(0x40)
_IRQ_NEIGHBOR_CELL_MEAS         = const(0x80)
_IRQ_LOCATION_FOUND             = const(0x100)
_IRQ_LOCATION_TIMEOUT           = const(0x200)
_IRQ_LOCATION_ERROR             = const(0x400)
_IRQ_GNSS_ASSISTANCE_REQUEST    = const(0x800)
_IRQ_CELL_LOCATION_REQUEST      = const(0x1000)

nic = network.CELL()    # This is a singleton, so we should only get it once

publish_msg = deque((), 5)      # For messaging from the IRQ handler, since we shouldn't be doing time consuming things like publishing in the handler

def irq_handler(event, data):
    if event == _IRQ_NW_REG_STATUS:
        # Data is the registration status, same as response to AT+CEREG?
        print(f'Registration status: {str(data)}')
    elif event == _IRQ_RRC_UPDATE:
        # Data is True if connected, False if idle
        print(f'RRC Mode: {"Connected" if data else "Idle"}')
    elif event == _IRQ_CELL_UPDATE:
        publish_msg.append((_IRQ_CELL_UPDATE, data))
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
            publish_msg.append((_IRQ_LOCATION_FOUND, 'gnss', data))
        elif (data[0] == "Cellular"):
            publish_msg.append((_IRQ_LOCATION_FOUND, 'cell',))

    elif event == _IRQ_LOCATION_TIMEOUT:
        print("Location timeout")
    elif event == _IRQ_LOCATION_ERROR:
        print("Location error")
    elif event == _IRQ_GNSS_ASSISTANCE_REQUEST:
        # Data is a list with the types of AGNSS data needed. The rest will be populated during the request
        publish_msg.append((_IRQ_GNSS_ASSISTANCE_REQUEST, data))
    elif event == _IRQ_CELL_LOCATION_REQUEST: 
        # Format of this data is: ((mcc, mnc, tac, cell_id, rsrp, rsrq, earfan), [(cell_id, earfcn, rsrp, rsrq),], Wi-Fi)
        publish_msg.append((_IRQ_CELL_LOCATION_REQUEST, data))
    else:
        print("Unknown interrupt: {}".format(event))

def button_publish(p, mqtt_client):
    if (p == board.button1):
        cloud.d2c({"appId":"BUTTON","messageType":"DATA","data": board.button1.value()})

def run():
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

    nic.irq(handler=irq_handler, mask=_IRQ_NW_REG_STATUS | _IRQ_RRC_UPDATE | _IRQ_CELL_UPDATE | _IRQ_PSM_UPDATE | _IRQ_EDRX_UPDATE |
                _IRQ_LOCATION_FOUND | _IRQ_LOCATION_TIMEOUT | _IRQ_LOCATION_ERROR | _IRQ_GNSS_ASSISTANCE_REQUEST | _IRQ_CELL_LOCATION_REQUEST)
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

    cloud = nRFCloudMQTT(nic, mqtt_device_id)
    cloud.connect()
    if cloud.isconnected():
        # Send data with the current device information
        cloud.d2c({'appId':'DEVICE','messageType':'DATA','data': {
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
        })

    board.button1.irq(lambda pin: button_publish(pin, cloud))
    nic.config(edrx=(81.92,5.12), edrx_enable=True)     # Set low power

    # First try GNSS with low accuracy (fewer satellites), then fallback to cellular.
    while nic.location(gnss=(120,0), cell=20, interval=1800) == -16: # -EBUSY
        nic.location_cancel()
        time.sleep(3)

    while True:
        time.sleep(1)
        if cloud.isconnected():
            if len(publish_msg):
                task = publish_msg.popleft()
                if task[0] == _IRQ_LOCATION_FOUND:
                    if task[1] == 'gnss':
                        gnss_index = 0
                        if len(task[2]) == 7:      # only additional GNSS data
                            gnss_index = 4
                        elif len(task[2]) == 14:   # Both
                            gnss_index = 11
                        # Publish all the received GNSS data
                        msg = {"appId":"GNSS","messageType":"DATA","data":{"lat":task[2][1],"lng":task[2][2],"acc":task[2][3]}}
                        if gnss_index != 0:
                            msg['data'].update(alt=task[2][gnss_index], hdg=task[2][gnss_index+1], spd=task[2][gnss_index+2])
                        # Now let's add some additional data, it can be any valid key/value pair.
                        # The extra data is not shown on the nRF Cloud portal, but it can be retrieved via REST API
                        msg['data']['extra'] = 80
                        cloud.d2c(msg)

                        # Let's publish temperature and humidity if the sensor is present
                        if sht20:
                            cloud.d2c({"appId":"TEMP", "messageType": "DATA", "data": sht20.temperature()})
                            cloud.d2c({"appId":"HUMID", "messageType": "DATA", "data": sht20.humidity()})
                    elif task[1] == 'cell':
                        # We don't need to publish location because Cell location is saved by nRF Cloud when
                        # the device sends the cell data to nRF Cloud for location information

                        # Let's publish temperature and humidity if the sensor is present
                        if sht20:
                            cloud.d2c({"appId":"TEMP", "messageType": "DATA", "data": sht20.temperature()})
                            cloud.d2c({"appId":"HUMID", "messageType": "DATA", "data": sht20.humidity()})
                elif task[0] == _IRQ_CELL_UPDATE:
                    # We have a new Cell ID, so let's get the latest network status
                    msg = {'appId':'DEVICE','messageType':'DATA','data': {
                        'networkInfo': {
                            'cellID': task[1][0],
                            'areaCode': task[1][1],
                            'mccmnc': nic.status("mccmnc"),
                            'currentBand': nic.status('band'),
                            'ipAddress': nic.status('ipAddress'),
                            'networkMode': 'LTE-M' if nic.status('mode') == network.LTE_MODE_LTEM else 'NB-IoT'
                        }
                    }}
                    cloud.d2c(msg)
                elif task[0] == _IRQ_GNSS_ASSISTANCE_REQUEST:
                    cloud.agnss_request(task[1])
                elif task[0] == _IRQ_CELL_LOCATION_REQUEST:
                    cloud.ground_fix(task[1][0], task[1][1])
                    pass
                else:
                    print(f'Unknown task submitted: {task[0]}')
                
            # This is needed for the MQTT Client to properly handle the keep alive as well
            # as any incoming messages (although this demo doesn't have any incoming messages)
            cloud.process()
        else:
            time.sleep(30)   # Additional delay for reconnections to give the network time to recover
            if nic.isconnected():
                cloud.connect()

def provision():
    mqtt_device_id = f'nrf-{nic.status("imei")}'

    nic.irq(handler=irq_handler, mask=_IRQ_NW_REG_STATUS | _IRQ_RRC_UPDATE | _IRQ_CELL_UPDATE)
    nic.connect()
    while not nic.isconnected():
        time.sleep(1)

    time.sleep(1)

    cloud = nRFCloudMQTT(nic, mqtt_device_id)

    while True:
        if cloud.connect() == 0:
            break
        else:
            time.sleep(30)

    cloud.disconnect()

if __name__ == "__main__":
    run()