import prefs

from mqtt_client import MQTTClient
from rest_client import RESTClient


def main():
    mqtt = MQTTClient()
    mqtt.start()
    rest = RESTClient()
    rest.start()


if __name__ == '__main__':
    logger = prefs.log_factory.get_new_logger("main")
    logger.info("TV-CWB-IOT Forwarder starting...")
    main()
