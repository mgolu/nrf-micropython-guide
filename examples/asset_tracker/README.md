# Asset Tracker

This sample shows how to use the nRF91xx to create an asset tracker posting the data
periodically to nRF Cloud.

## Installation

Install the board support file which provides easier access to the buttons
and LEDs on the board:

    $ mpremote <device> cp ../../helper_scripts/board_support/nrf9160dk.py :nrf9160dk.py

Install the `umqtt.py` file. This is mostly based on the `umqtt.py` file from
the micropython-lib, but customized to the offloaded TLS sockets that are
used on nRF91xx devices.

    $ mpremote <device> cp ../../helper_scripts/umqtt.py :umqtt.py

Modify the ``tracker.py`` file TEAM_ID definition. You can find the Team ID in the Teams page
on the nRF Cloud portal. See more information [here](https://docs.nrfcloud.com/AccountAndTeamManagement/Teams/TeamsOverview.html#team-id).

Install the ``tracker.py`` file. 

    $ mpremote <device> cp tracker.py :tracker.py

## Running the sample

Run the `tracker.py` file. This will make a connection to nRF Cloud and 
post the location of the device, in addition to other data, every 5 minutes.
You can see the data come in on the nRF Cloud dashboard for the device.

### Customizing the program

Changing `TEAM_ID` is necessary as detailed above. There are other modifications
you can make.

In the block below, the location is requested very 5 minutes (the interval). Each time,
the nRF91xx will attempt a GNSS fix for up to 120 seconds, and accept lower accuracy
(the 0 in the `gnss=(120,0)` tuple). If GNSS doesn't get a fix, it will send tower
data to nRF Cloud for a cellular location, with a timeout of 20 seconds.
```python
# First try GNSS with low accuracy (fewer satellites), then fallback to cellular.
nic.location(gnss=(120,0), cell=20, interval=300)
```
You can also change what custom data is published in the `while True` loop by changing
the `c.publish` commands.
