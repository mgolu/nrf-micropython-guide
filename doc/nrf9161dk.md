# nRF9161DK device guide

## Installation

> **_NOTE_**: If you will be using cellular location or want to speed up GNSS location by using `AGPS`, the development kit needs to be connected to nRF Cloud to get the data. Follow [these steps](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/device_guides/working_with_nrf/nrf91/nrf9160_gs.html#connecting-the-dk-to-nrf-cloud) before installing Micropython on it or while running a MicroPython program that tries
to connect to nRF Cloud (like the Asset Tracker example). This only needs to be done once.

- Download the `nrf9161dk_merged.hex` file from the [firmware directory](/firmware/).
- Download the latest [modem firmware](https://www.nordicsemi.com/Products/nRF9161/Download?lang=en#infotabs). It should be named 
`mfw_nrf9160_2.x.x.zip`. Do NOT unzip the file.
- Install [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-desktop) 
- Use the [Programmer](https://infocenter.nordicsemi.com/topic/ug_nc_programmer/UG/nrf_connect_programmer/ncp_application_overview.html?cp=11_3_2_2) application to program the modem firmware and application Hex file onto your development kit.

## Usage

The interface chip on the nRF9161DK exposes 2 virtual COM ports. The first one is where you will find the MicroPython REPL prompt.

### Filesystem

The first time that you use the device you might need to create the filesystem. You can do that from the REPL prompt:

```python
import os
from zephyr import FlashArea

block_dev = FlashArea(FlashArea.STORAGE, 4096)
os.VfsLfs2.mkfs(block_dev)
os.mount(block_dev, '/flash')
```

### Buttons and LEDs

There are four buttons:
- Button 1: It can be used with `Pin.cpu.gpio0_8`
- Button 2: If pressed at boot time, the board will skip executing a `main.py` file from the filesystem. During normal operation, it can be used with `Pin.cpu.gpio0_9`
- Button 3: It can be used with `Pin.cpu.gpio0_18`
- Button 4: It can be used with `Pin.cpu.gpio0_19`

There are four LEDs:
- LED1: Can be accessed with `Pin.cpu.gpio0_0`
- LED2: Can be accessed with `Pin.cpu.gpio0_1`
- LED3: Can be accessed with `Pin.cpu.gpio0_4`
- LED4: Can be accessed with `Pin.cpu.gpio0_5`


## Pins and GPIO
```python
from machine import Pin

pin = Pin(Pin.cpu.gpio0_2, Pin.OUT)
```
## I2C

The available bus is `i2c2` and this is how you get an instance:
```python
from machine import I2C

i2c = I2C('i2c2')
```

## Cellular interface

The Cellular interface is part of the `network` module. You can get an instance with the following example:
```python
import network
nic = network.CELL()
nic.connect()
```

Once connected, you can use sockets with some modifications.

## Sockets

The nRF91 family of devices has its own sockets, which is offloaded from the main 
operating system. While there are virtually no difference with how other Micropython
ports handle TCP and UDP sockets, there are some bigger differences when using SSL/TLS.

Specifically, the `ssl` module is not used. This results in less memory usage for the
processor, as the nRF91 handles all TLS encryption.

### TLS Credentials

It's important to understand credential management. Instead of using the SSL Context 
to load certificates in memory, the credentials are loaded onto the flash of the modem.
This means that credentials only need to be loaded once, even across reboots. The modem
has Security Tags which can have Root CA certificates, Client certificates, Keys, etc.
These Security Tags are then specified when opening a socket.

> **_NOTE_** The security tag 16842753 is used for nRF Cloud and should not be deleted
or used for other purposes. If you are not using a Development Kit or Thingy, you first
need to generate the credentials and load the AWS CA certificate. See
[these instructions.](https://docs.nordicsemi.com/bundle/nrf-cloud/page/Devices/Security/Credentials.html#generating-credentials-using-at-commands)

#### Credential types

For the commands below, these are the credential types:
```
0 – Root CA certificate (ASCII text).
1 – Client certificate (ASCII text).
2 – Client private key (ASCII text).
3 – PSK (ASCII text in hexadecimal string format).
4 – PSK identity (ASCII text).
5 – Public key (ASCII text). Used in authenticated AT commands.
6 – Device identity public key.
```

#### CELL.cert(action[, args])

The available actions are:

* ``list``: returns a list of the programmed credentials. Each credential is a tuple
with two values: `(sec_tag, type)`. You can also filter to limit the list to a specific
`sec_tag` or even a `sec_tag` and `type`.

```python
nic.cert('list')         # List of all programmed credentials
nic.cert('list', 100)    # List of credentials for sec_tag 100
nic.cert('list', 100, 0) # List of Root CA certificate for sec_tag 100
```

* ``delete``: deletes a specific credential. Both `sec_tag` and `type` are required arguments.

```python
nic.cert('delete', 100, 1)  # Delete the Client certificate for sec_tag 100
```

* ``write``: write a specific credential. Both `sec_tag` and `type` are required arguments.
Certificates noted as `ASCII text` must be in PEM format.

```python
# Read the CA certificate from flash, and write to sec_tag 100
with open('/flash/ca_cert.pem', 'r') as f:
    ca_data = f.read()
    nic.cert('write', 100, 0, ca_data)
```

### TLS sockets

Because the socket and TLS encryption is offloaded, the standard Micropython way of 
wrapping sockets with the `ssl` module after being created doesn't work. Instead, the
socket needs to be created as a TLS socket.

The API to create a socket is:
```python
socket.socket(family, socktype, proto, sec_tag[, verify[, hostname]])
```

``family`` is required and can be ``socket.AF_INET`` or ``socket.AF_INET6``

``socktype`` is required and must be ``socket.SOCK_STREAM`` (future enhancement to add UDP)

``proto`` is required and must be ``socket.IPPROTO_TLS_1_2`` (future enhancement to add DTLS)

`sec_tag` is required and must match installed credentials. 

`verify` is optional and can be `socket.TLS_PEER_VERIFY_NONE`, `socket.TLS_PEER_VERIFY_OPTIONAL`, or `TLS_PEER_VERIFY_REQUIRED` (default).

If `verify` is included, you can also include `hostname` which must be a string. 
If included, then Server Name Identification (SNI) is used.

### Specifics of the CELL class

#### CELL.connect()

No parameters are accepted. The cellular modem will start attempting to connect to the cellular network.

     nic.connect()

#### CELL.status([param])

Return the current status of the cellular connection.

When called with no argument the return value describes the network 
link status. The values are the same as found here: https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/modem/lte_lc.html#c.lte_lc_nw_reg_status

When called with one argument *param* should be a string naming the status parameter to retrieve.

``'mode'``: The possible statuses are defined as constants:

* ``0`` -- not connected
* ``network.LTE_MODE_LTEM`` -- connected to LTE Cat M1 network
* ``network.LTE_MODE_NBIOT`` -- connected to NB-IoT network


#### CELL.config('param')
#### CELL.config(param=value, ...)

Get or set general network interface parameters. For setting parameters, keyword argument syntax should be used,
multiple parameters can be set at once. For querying, parameters name should
be quoted as a string, and only one parameter can be queries at a time:


Following are commonly supported parameters:

```mode```: Set the allowed and preferred network modes, with a tuple 
that has the allowed as the first parameter, and preferred second.
The values are a combination of ``network.LTE_MODE_LTEM``,
``network.LTE_MODE_NBIOT`` and ``network.LTE_MODE_GPS``.

Note that the modem must not be connected or trying to connect to change this configuration.

For example, to support both networks and GPS, and prefer Cat M1:

```python
nic.config(mode=(network.LTE_MODE_LTEM | network.LTE_MODE_NBIOT | network.LTE_MODE_GPS,network.LTE_MODE_LTEM))
```

A special value for preference is `0`, which means no preference. 


```psm_params```: Request values for Power Save Mode. This is a tuple
with two values: (TAU, RAT). The value definitions are found here:
https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/modem/lte_lc.html#c.lte_lc_psm_param_set

These values are requested. In order to know what values were sent
by the network, you must register an interrupt and get the values from
the ``_IRQ_PSM_UPDATE`` interrupt.

```psm_enable```: True for enabling Power Save Mode, False to disable it.

#### CELL.irq(handler=irq_handler, mask=irq_mask)

Register an ``irq_handler`` to get events from the cellular device. To save space all the 
interrupts are not defined as module constants. You can instead add the ones needed to your
Python scripts:

```python
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
```

#### CELL.uuid()

Get the device's UUID, from the internal JWT. This can be used as the Device ID when connecting
to nRF Cloud if the device has been provisioned with the UUID.

#### CELL.imei()

Get the modem's IMEI. This can be used for reporting to a system that wants to keep track
of IMEIs. It can also be used as the Device ID for connecting to nRF Cloud if the device is
on a Development Kit that has been provisioned into nRF Cloud with the Device ID `nrf-<imei>`.

## Location Services

#### CELL.location([args])

Get the location of the device, using GNSS, cellular location, or both. 
The arguments can be:

* ``gnss``: set the timeout for getting GNSS location in seconds. If a tuple, the first value is the timeout, the second is the accuracy, and the third is satellite visibility detection.
> **_NOTE_**: if the device is connected to nRF Cloud, it will use `AGPS` to speed up the time to GNSS fix.

* ``cell``: set the timeout for getting the cellular location in seconds. If a tuple, the first value is a timeout, and the second the number of cell towers to detect. The location is reported back to the device from nRF Cloud and sent via the `_IRQ_LOCATION_FOUND` interrupt. It is also stored in nRF Cloud, and you can view it on your device's dashboard
> **_NOTE_**: requires the device to connect to nRF Cloud to get the approximate location from the detected tower data.

* ``interval``: how often to get the location, in seconds. If not used, location is requested once
* ``all``: True to get location using all methods, False to use the first method listed, and only use the next as a fallback if the first fails.

The order of the arguments sets the order in which they are used. An interrupt
will be called when the location is found or if there is a timeout.

Example:

```python
    def irq_handler(event, data):
        if event == _IRQ_LOCATION_FOUND:
            print("Location found via {}: Latitude {}, Longitude {}, accuracy {}".format(data[0], data[1], data[2], data[3]))
            if data[4]:
                print("Location found on {}/{}/{} at {}:{:2d}:{:2d}.{:3d}".format(data[4], data[5], data[6], data[7], data[8], data[9], data[10]))
        elif event == _IRQ_LOCATION_TIMEOUT:
            print("Location timeout")
        elif event == _IRQ_LOCATION_ERROR:
            print("Location error")
        
    nic.irq(handler=irq_handler, mask=_IRQ_LOCATION_FOUND | _IRQ_LOCATION_TIMEOUT | _IRQ_LOCATION_ERROR)
    nic.connect()
    while not nic.isconnected():
        time.sleep(1)
    nic.location(gnss=(120,0), cell=20, interval=240) # Try GNSS for 120 seconds, then fallback to cellular with 20 second timeout if GNSS fails
```

#### CELL.location_cancel()

Cancel a location request.
