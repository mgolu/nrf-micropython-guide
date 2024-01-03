from micropython import const
from umqtt import MQTTClient
import network
import time
from machine import Pin
import nrf9160dk as board

DEFAULT_SEC_TAG = const(100)
CA_CERT_TYPE = const(0)
MQTT_SERVER = "broker.hivemq.com"
CA_CERT_FILE = "/flash/starfieldCA.pem"
MQTT_PUB_TOPIC = b"/micropython/zephyr/button"
MQTT_SUB_TOPIC = b"/micropython/zephyr/led"

# Check if the CA certificate is installed on the modem. If not, install it.
def check_cacert(nic):
    if not nic.cert('list', DEFAULT_SEC_TAG, CA_CERT_TYPE):
        # install_cert
        with open(CA_CERT_FILE, 'r') as f:
            ca_data = f.read()
            nic.cert('write', DEFAULT_SEC_TAG, CA_CERT_TYPE, ca_data)

def button_press(p, c):
    if (p == board.button1 and board.button1.value() == 0):
        c.publish(MQTT_PUB_TOPIC, b"1")
    elif (p == board.button2 and board.button2.value() == 0):
        c.publish(MQTT_PUB_TOPIC, b"2")

def mqtt_callback(topic, msg):
    if msg == b'1':
        board.led1.on() if board.led1.value() == 0 else board.led1.off()
    elif msg == b'2':
        board.led2.on() if board.led2.value() == 0 else board.led2.off()
    elif msg == b'3':
        board.led3.on() if board.led3.value() == 0 else board.led3.off()
    elif msg == b'4':
        board.led4.on() if board.led4.value() == 0 else board.led4.off()

def run():
    nic = network.CELL()
    nic.active(True)
    check_cacert(nic)
    if not nic.isconnected():
        nic.connect()
        while not nic.isconnected():
            time.sleep(1)

    time.sleep_ms(200)

    try:
        # Modify this call. For example, change ssl=False if not using SSL.
        c = MQTTClient("umqtt_client", MQTT_SERVER, ssl=True, ssl_params={'sec_tag': DEFAULT_SEC_TAG})
        c.set_callback(mqtt_callback)
        c.connect()

        c.subscribe(MQTT_SUB_TOPIC)
        board.button1.irq(lambda pin: button_press(pin, c))
        board.button2.irq(lambda pin: button_press(pin, c))
        print("MQTT connection established")

        while True:
            c.check_msg()
            time.sleep_ms(1000)
    finally:
        c.disconnect()

if __name__ == "__main__":
    run()
