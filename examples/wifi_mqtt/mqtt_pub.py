from umqtt.simple import MQTTClient
import network
import time

def main(server="test.mosquitto.org"):
    nic = network.WLAN(network.STA_IF)
    if nic.isconnected() is False:
        nic.credential('connect','GuestHouse')
    try:
        while nic.isconnected() is False:
            time.sleep_ms(100)
    except KeyboardInterrupt:
        pass
    time.sleep_ms(1000)
    c = MQTTClient("umqtt_client", server, ssl=True)
    c.connect()
    c.publish(b"/test/mine/hello", b"hello")
    c.disconnect()


if __name__ == "__main__":
    main()