import network
import time
from micropython import const

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
        print("Location found via {}: Latitude {}, Longitude {}, accuracy {}".format(data[0], data[1], data[2], data[3]))
        if data[4]:
            print("Location found on {}/{}/{} at {}:{:2d}:{:2d}.{:3d}".format(data[4], data[5], data[6], data[7], data[8], data[9], data[10]))
    elif event == _IRQ_LOCATION_TIMEOUT:
        print("Location timeout")
    elif event == _IRQ_LOCATION_ERROR:
        print("Location error")
    else:
        print("Unknown interrupt: {}".format(event))


def run():
    nic = network.CELL()
    nic.irq(handler=irq_handler, mask=_IRQ_NW_REG_STATUS | _IRQ_RRC_UPDATE | _IRQ_PSM_UPDATE | _IRQ_LOCATION_FOUND | _IRQ_LOCATION_TIMEOUT | _IRQ_LOCATION_ERROR)
    nic.connect()
    while not nic.isconnected():
        time.sleep(1)

    # First try GNSS with low accuracy (fewer satellites), then fallback to cellular.
    nic.location(gnss=(60,0), cell=20)

    try:
        while True:
            time.sleep_ms(100)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()
