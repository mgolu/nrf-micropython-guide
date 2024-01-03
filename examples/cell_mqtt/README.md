# MQTT example

This sample implements MQTT in MicroPython, using the nRF91xx devices to 
send data to an MQTT broker using the Cellular interface.

## Installation

Install the board support file which provides easier access to the buttons
and LEDs on the board:

    $ mpremote <device> cp ../board_support/nrf9160dk.py :nrf9160dk.py

Install the `umqtt.py` file. This is mostly based on the `umqtt.py` file from
the micropython-lib, but customized to the offloaded TLS sockets that are
used on nRF91xx devices.

    $ mpremote <device> cp umqtt.py :umqtt.py

Install the ``mqtt_cell.py``. Make sure to make any necessary modifications here,
for example if not using TLS, as well as the MQTT server, publish and
subscribe topics.

    $ mpremote <device> cp mqtt_cell.py :mqtt_cell.py

If using TLS, then install the certificate. For using HiveMQ's free broker, 
the Starfield CA certificate is included here:

    $ mpremote <device> cp starfieldCA.pem :starfieldCA.pem

## Running the program

Run the `mqtt_cell.py` file. This will connect to the MQTT Broker and
subscribe to the `MQTT_SUB_TOPIC`. 

Use another device to send a number between 1-4 to the topic. That will
toggle the appropriate LED on the development kit. 

For example, this command will toggle LED 2:

    mosquitto_pub -h broker.hivemq.com -p 1883 -t '/micropython/zephyr/led' -m 2

Press button 1 or button 2 on the DK to send a message to `MQTT_PUB_TOPIC` with the number of the button pressed. You can
monitor this with the following command:

    mosquitto_sub -h broker.hivemq.com -p 1883 -t '/micropython/zephyr/button'


