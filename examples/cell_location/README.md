# Location example

This sample shows how to set an interrupt handler for a number of
interrupts coming from the nRF91 modem, as well as get the location with
GNSS or cellular networks.

To use cellular networks, it requires the DK to be added to nRF Cloud.

## Installation

Copy the file into the filesystem:

    $ mpremote <device> cp location.py :location.py

## Running the program

Run the `location.py` file. By default it will attempt GNSS for 60 seconds
and if that fails it will detect the cellular towers and use nRF Cloud to
get a triangulated location.

Note that the GNSS also uses nRF Cloud AGPS in order to speed up time to 
first fix. If the DK is not in your nRF Cloud account, then the AGPS call
will not result in data and the time to first fix will be much longer.
