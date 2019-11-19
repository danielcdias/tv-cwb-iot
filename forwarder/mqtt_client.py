import time
import paho.mqtt.client as mqtt
import message_queue as queue

from prefs import log_factory, prefs
from mail_sender import MailSender
from threading import Thread, Event

stop_timer_flag = Event()  # Flag to stop timer if reconnection occurs before MQTT_DISCONNECTION_EMAIL_NOTIFY_TIMEOUT

logger = None


def get_logger():
    global logger
    if not logger:
        logger = log_factory.get_new_logger("mqtt_client")
    return logger


class DisconnectionTimer(Thread):
    def __init__(self, event):
        Thread.__init__(self)
        self.stopped = event
        self.sent = False

    def run(self):
        while (not self.stopped.wait(prefs['email']['notification_timeout'])) and (not self.sent):
            email = MailSender()
            email.send_message(prefs['email']['subject'], fromaddr=prefs['email']['from'], to=prefs['email']['to'],
                               body="Desconexão ocorrida com o broker MQTT.")
            self.sent = True


class MQTTClient(Thread):

    def __init__(self):
        super(MQTTClient, self).__init__()
        self.mqttc_cli = mqtt.Client(client_id=prefs['mqtt']['connection']['client-id'])
        self.is_running = False

    def on_connect(self, client, userdata, flags, rc):
        stop_timer_flag.set()
        get_logger().info("Connection started with {}, {}, {}, {}.".format(client, userdata, flags, rc))

    def on_disconnect(self, client, userdata, rc):
        get_logger().warning("Connection finished with {}, {}, {}.".format(client, userdata, rc))
        stop_timer_flag.clear()
        thread = DisconnectionTimer(stop_timer_flag)
        thread.start()

    def on_message(self, client, userdata, message):
        get_logger().debug("Message received from {}, {}, message: {}, {}, {}, {}.".format(client, userdata, message.topic,
                                                                                     message.payload, message.qos,
                                                                                     message.retain))
        board_id = (message.topic[-8:-4] if len(message.topic) > 24 else message.topic[-4:])
        sensor_id = (message.topic[-3:] if len(message.topic) > 24 else None)
        payload = message.payload.decode()
        if MQTTClient.is_valid_payload(payload):
            if queue.add_message(message.topic, payload):
                if not sensor_id:
                    if payload[0:3] in prefs['mqtt']['status'].values():
                        self.send_command(board_id, prefs['mqtt']['commands']['timestamp'],
                                          MQTTClient.get_time_in_seconds())
            else:
                get_logger().error("Messsge received could not be saved in the queue.")
        else:
            get_logger().warning("Payload received is not well formatted: {}.".format(payload))

    def on_publish(self, client, userdata, mid):
        get_logger().debug("Message published to {}, {}, {}.".format(client, userdata, mid))

    def on_subscribe(self, client, userdata, mid, granted_qos):
        get_logger().debug("Subscribed {}, {}, {}, {}.".format(client, userdata, mid, granted_qos))

    def on_log(self, mqttc, obj, level, string):
        pass

    def is_running(self):
        return self.is_running

    def run(self):
        get_logger().info("Starting MQTT client...")
        connected = False
        email_sent = False
        while True:
            if not connected:
                try:
                    self.mqttc_cli.on_connect = self.on_connect
                    self.mqttc_cli.on_subscribe = self.on_subscribe
                    self.mqttc_cli.on_publish = self.on_publish
                    self.mqttc_cli.on_message = self.on_message
                    self.mqttc_cli.on_disconnect = self.on_disconnect
                    self.mqttc_cli.on_log = self.on_log
                    self.mqttc_cli.reconnect_delay_set(min_delay=1, max_delay=30)
                    get_logger().debug("Connecting to MQTT broker on {}:{}, with timeout = {}.".format(
                        prefs['mqtt']['connection']['host'], prefs['mqtt']['connection']['port'],
                        prefs['mqtt']['connection']['timeout']))
                    self.mqttc_cli.connect(prefs['mqtt']['connection']['host'], prefs['mqtt']['connection']['port'],
                                           prefs['mqtt']['connection']['timeout'])
                    self.mqttc_cli.subscribe(prefs['mqtt']['topics']['status'], 0)
                    self.is_running = True
                    connected = True
                    email_sent = False
                    self.mqttc_cli.loop_start()
                except (ConnectionRefusedError, TimeoutError) as ex:
                    if not email_sent:
                        email = MailSender()
                        email.send_message(prefs['email']['subject'], fromaddr=prefs['email']['from'],
                                           to=prefs['email']['to'],
                                           body="Não foi possível conectar servidor ao broker MQTT.")
                        email_sent = True
                    get_logger().error("Cannot connect to MQTT broker! Exception: {}".format(ex))
            time.sleep(5)

    def send_command(self, board_id: str, cmd: str, value: int) -> bool:
        result = False
        try:
            buf = cmd + str(value)
            queue_cmd = prefs['mqtt']['topics']['command'] + board_id
            get_logger().debug("Sending to queue {} - command {}".format(queue_cmd, buf))
            self.mqttc_cli.publish(queue_cmd, buf)
            result = True
        except (ValueError, ConnectionError, ConnectionRefusedError) as ex:
            get_logger().exception("Cannot publish to command topic! Exception: {}".format(ex))
        return result

    @staticmethod
    def get_time_in_seconds() -> int:
        return int(round(time.time()))

    @staticmethod
    def is_valid_payload(payload: str) -> bool:
        result = (payload in (prefs['mqtt']['status']['startup'],
                              prefs['mqtt']['status']['timestamp-update-request'])) or \
                 ((len(payload) >= 12) and (payload.find(prefs['mqtt']['commands']['timestamp']) > -1))
        return result
