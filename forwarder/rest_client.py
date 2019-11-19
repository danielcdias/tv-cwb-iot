import requests
import time
import json

from encryption_tools import decrypt
from mail_sender import MailSender
import message_queue as queue
from prefs import log_factory, prefs
from threading import Thread

TOKEN_KEY = "Authorization"
TOKEN_VALUE_FORMAT = "Token {}"
CONTENTTYPE_KEY = "Content-Type"
CONTENTTYPE_VALUE = "application/json"

logger = None


def get_logger():
    global logger
    if not logger:
        logger = log_factory.get_new_logger("rest_client")
    return logger


class RESTClient(Thread):

    def __init__(self):
        super(RESTClient, self).__init__()
        self._token = ""

    def retrieve_token(self) -> bool:
        result = False
        try:
            data = {'username': decrypt(prefs['web-service']['username']),
                    'password': decrypt(prefs['web-service']['password'])}
            url = prefs['web-service']['base_url'] + prefs['web-service']['get_token_service']
            resp = requests.post(url, data=data, timeout=prefs['web-service']['timeout'])
            if resp.status_code == 200:
                self._token = resp.json()['token']
                result = True
            else:
                get_logger().error("Token for REST API could not be retrieved. Status code = {}, Content = {}".format(
                    resp.status_code, resp.text))
        except Exception as ex:
            get_logger().error("Could not retrieve token due to an exception: {}".format(ex))
        return result

    def send_message(self, message: dict):
        try:
            url = prefs['web-service']['base_url'] + prefs['web-service']['message_receiver_service']
            headers = {
                CONTENTTYPE_KEY: CONTENTTYPE_VALUE,
                TOKEN_KEY: TOKEN_VALUE_FORMAT.format(self._token)
            }
            data = {"topic": message['topic'], "message": message['payload']}
            resp = requests.post(url, headers=headers, data=json.dumps(data), timeout=prefs['web-service']['timeout'])
            if resp.status_code == 201:
                if queue.update_message(message['id'], queue.FLAG_SENT):
                    get_logger().debug("Message {} sent with success!".format(message))
                else:
                    get_logger().error("Sent flag could not be updated in the queue db.")
            elif resp.status_code == 401:
                self.retrieve_token()
            else:
                get_logger().error(
                    "Message could not be sent. Headers sent: {}, Data sent: {}, "
                    "Status code {}, Headers {}, Content: {}".format(
                        headers, data, resp.status_code, resp.headers, resp.text))
                flag_to_update = queue.FLAG_ERROR_OTHER
                if resp.text.startswith('"No control board was found with mac address ending with'):
                    flag_to_update = queue.FLAG_ERROR_NO_BOARD
                elif resp.text.startswith('"No sensor was found with ID'):
                    flag_to_update = queue.FLAG_ERROR_NO_SENSOR
                if not queue.update_message(message['id'], flag_to_update):
                    get_logger().error("Sent flag could not be updated in the queue db.")
        except Exception as ex:
            get_logger().error("Could not send message due to an exception: {}".format(ex))

    def run(self):
        get_logger().info("Starting REST client connecting to base URL {}".format(prefs['web-service']['base_url']))
        if self.retrieve_token():
            while True:
                for message in queue.get_all_not_sent():
                    self.send_message(message)
                time.sleep(1)
        else:
            get_logger().error("Abandoning thread...")
            email = MailSender()
            email.send_message(prefs['email']['subject'], fromaddr=prefs['email']['from'], to=prefs['email']['to'],
                               body="Thread REST client encerrada. Verificar logs.")
