# Asset Tracker

This sample shows how to use the nRF91xx to create an asset tracker posting the data
periodically to nRF Cloud.

## Installation
### Board helper file
Install the board support file which provides easier access to the buttons
and LEDs on the board:

    $ mpremote <device> cp ../../helper_scripts/board_support/nrf9161dk.py :nrf9161dk.py

### MQTT helper files
Install the `umqtt.py` file. This is mostly based on the `umqtt.py` file from
the micropython-lib, but customized to the offloaded TLS sockets that are
used on nRF91xx devices.

Also install the `nrfcloud_mqtt.py` from the helper_scripts folder.

    $ mpremote <device> cp ../../helper_scripts/umqtt.py :umqtt.py
    $ mpremote <device> cp ../../helper_scripts/nrfcloud_mqtt.py :nrfcloud_mqtt.py

### Tracker file
Modify the `tracker.py` file to import the correct board file. By default, it is
using the nRF9161DK helper file:

```python
# Import the right file for your board here
import nrf9161dk as board
```
After modifying (if necessary), install it:

    $ mpremote <device> cp tracker.py :tracker.py

## Running the sample

Run the `tracker.py` file. 

### Provisioning into nRF Cloud


If the Development Kit has not yet been provisioned to nRF Cloud, then you will 
first need to add it to your nRF Cloud account. If the DK has never accessed nRF Cloud, 
you need to make a connection first. You can run this from REPL:

```python
>>> import tracker
>>> tracker.provision()
```
While that is running, navigate to your nRF Cloud dashboard and add the device.

### Running the Asset Tracker
If the Development Kit has already been provisioned into your nRF Cloud account,
then you can start running the Asset Tracker part of the sample:

```python
>>> import tracker
>>> tracker.run()
```

This will make a connection to nRF Cloud and 
post the location of the device, in addition to other data, every 30 minutes.
You can see the data come in on the nRF Cloud dashboard for the device.

Pressing Button 1 on the development kit will send data to the Button information
card in nRF Cloud.

Pressing Button 2 will enable or disable the console port. This allows you to achieve
the lowest possible power consumption by not keeping the UART RX clock running. The
application by default requests eDRX, also to lower power consumption.

### Customizing the program

In the block below, the location is requested very 30 minutes (the interval). Each time,
the nRF91xx will attempt a GNSS fix for up to 120 seconds, and accept lower accuracy
(the 0 in the `gnss=(120,0)` tuple). If GNSS doesn't get a fix, it will send tower
data to nRF Cloud for a cellular location, with a timeout of 20 seconds.
```python
# First try GNSS with low accuracy (fewer satellites), then fallback to cellular.
nic.location(gnss=(120,0), cell=20, interval=1800)
```
You can also change what custom data is published in the `while True` loop by changing
the `cloud.d2c` commands.
