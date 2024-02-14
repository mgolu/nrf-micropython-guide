from umqtt import MQTTClient
import json
import time

# Get the _TEAM_ID value from your Team ID in nRF Cloud. Leave "" to use the shadow
_TEAM_ID = ""
_MQTT_KEEPALIVE = 1200    # in seconds

class nRFCloudMQTT:
    State = {"DISCONNECTED": 0, "CONNECTED": 1, "SHADOW_RETRIEVED": 2, "UNPAIRED": 3, "PAIRED": 4}
    def __init__(self, nic, device_id: str):
        DEFAULT_SEC_TAG = const(16842753)  # nRF Cloud default sec_tag
        self.nic = nic
        self.device_id = device_id
        self.prefix = f'prod/{_TEAM_ID}/'
        self.mqtt_client = MQTTClient(device_id, "mqtt.nrfcloud.com", keepalive=_MQTT_KEEPALIVE, ssl=True, ssl_params={'sec_tag': DEFAULT_SEC_TAG})
        self.mqtt_client.set_callback(self._cloud_process)
        self.status = self.State["DISCONNECTED"]

    def _cloud_process(self, topic, msg):
        if (topic.decode().endswith('agnss/r')):
            # Response to AGNSS
            self.nic.agnss_data(msg)
        elif (topic.decode().endswith('ground_fix/r')):
            # Response to SCELL, MCELL, and Wi-Fi location
            resp = json.loads(msg.decode())
            if resp['appId'] == 'GROUND_FIX':
                self.nic.location_cloud_fix(resp['data']['lat'], resp['data']['lon'], resp['data']['uncertainty'])
        elif (topic.decode().endswith('shadow/get/accepted')):
            # Response with the shadow, to get topics and pairing status
            shadow = json.loads(msg.decode())
            if shadow['desired']['pairing']['state'] != 'paired':
                self.status = self.State["UNPAIRED"]
            else:
                self.prefix = shadow['desired']['nrfcloud_mqtt_topic_prefix']
                self.status = self.State["PAIRED"]

    def connect(self) -> int:
        if self.mqtt_client.connect() == 0:
            self.status = self.State["CONNECTED"]

            # If _TEAM_ID is set to "", then go get the shadow
            if self.prefix == 'prod//':
                self.mqtt_client.subscribe(f'{self.device_id}/shadow/get/accepted'.encode())
                self.get_shadow()
                retries = 0
                while self.status < self.State["SHADOW_RETRIEVED"]:
                    time.sleep_ms(500)
                    try:
                        self.mqtt_client.process()
                    except:
                        return -1
                    retries += 1
                    if retries > 20:       # Wait for 10 seconds
                        print("Could not retrieve shadow, ensure device is provisioned to your nRF Cloud account")
                        self.disconnect()
                        return -1
            else:       # _TEAM_ID is manually set
                self.status = self.State["PAIRED"]

            if self.status == self.State["PAIRED"]:
                # Subscribe to the topics to receive AGNSS and Cellular location
                self.mqtt_client.subscribe(f'{self.prefix}m/d/{self.device_id}/agnss/r'.encode())
                self.mqtt_client.subscribe(f'{self.prefix}m/d/{self.device_id}/ground_fix/r'.encode())
                print("Connected to nRF Cloud")
                return 0
            elif self.status <= self.State["UNPAIRED"]:
                # Device is not paired, so we are not able to send data
                print(f'Device is unpaired, add it to your nRF Cloud account: {self.device_id}')
                self.mqtt_client.disconnect()
                return -1
            else:
                # Some other issue
                self.mqtt_client.disconnect()
                return -1
        else:
            print("Connection to nRF Cloud failed")
            return -1

    def disconnect(self) -> None:
        self.status = self.State["DISCONNECTED"]
        self.mqtt_client.disconnect()
    
    # This uses the Device to Cloud messaging to send the message. See:
    # https://docs.nrfcloud.com/APIs/MQTT/Topics.html#message-topics
    def d2c(self, msg: dict) -> int:
        """ Send a message to nRF Cloud using Device to Cloud messaging """
        try:
            self.mqtt_client.publish(f'{self.prefix}m/d/{self.device_id}/d2c'.encode(), json.dumps(msg).encode())
        except:
            print("Sending data to nRF Cloud failed")
            self.disconnect()
            return -1
        return 0

    def get_shadow(self):
        try:
            self.mqtt_client.publish(f'$aws/things/{self.device_id}/shadow/get'.encode(), b'')
        except:
            print("Getting shadow failed")
            self.disconnect()

    def agnss_request(self, types: list) -> None:
        mccmnc = self.nic.status("mccmnc")
        msg = {'appId': 'AGNSS', 'messageType': 'DATA', 'data': {
            'mcc': int(mccmnc[:3]),
            'mnc': int(mccmnc[3:]),
            'tac': int(self.nic.status("area"), 16),
            'eci': int(self.nic.status("cellid"), 16),
            'rsrp': self.nic.status("rsrp"),
            'types': types,
            # Change this if you want all the AGSS data
            'filtered': True,
            'mask': 5
        }}
        self.d2c(msg)

    def ground_fix(self, cell, ncells):
        msg = {'appId': 'GROUND_FIX', 'messageType': 'DATA', 'data': {}, 'config': {
            'doReply': True,       # Set to False to not receive a response with location. Location is still saved in nRF Cloud
            'hiConf': False        # False: 68% confidence device is in uncertainty circle. True: 95% confidence (circle will be larger)
        }}
        if cell:
            msg['data']['lte'] = [{
                'mcc': cell[0],
                'mnc': cell[1],
                'tac': cell[2],
                'eci': cell[3],
                'rsrp': cell[4],
                'rsrq': cell[5],
                'earfcn': cell[6]
            }]
        else:
            mccmnc = self.nic.status("mccmnc")
            msg['data']['lte'] = [{
                'mcc': int(mccmnc[:3]),
                'mnc': int(mccmnc[3:]),
                'tac': int(self.nic.status("area"), 16),
                'eci': int(self.nic.status("cellid"), 16),
                'rsrp': self.nic.status("rsrp")
            }]
        if ncells:
            msg['data']['lte'][0]['nmr'] = []
            for ncell in ncells:
                msg['data']['lte'][0]['nmr'].append({
                    'pci': ncell[0],
                    'earfcn': ncell[1],
                    'rsrp': ncell[2],
                    'rsqr': ncell[3]
                })

        self.d2c(msg)
        if not msg['config']['doReply']:
            # We're not going to get a response from the Cloud, so let's tell the Location system that
            # we were successful to avoid a timeout
            self.nic.location_cloud_fix(0,0,0)

    def isconnected(self) -> bool:
        return True if self.status >= self.State["PAIRED"] else False
    
    def process(self) -> None:
        if self.isconnected():
            try:
                self.mqtt_client.process()
            except:
                print("Connection error, disconnecting")
                self.disconnect()