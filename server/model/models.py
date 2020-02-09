import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


def check_mac_address(value):
    if not re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", value.lower()):
        raise ValidationError(
            _('Invalid MAC address '),
        )


class BoardVendor(models.Model):
    description = models.CharField(max_length=100, unique=True, verbose_name="Descrição")

    objects = models.Manager()

    def __str__(self):
        return self.description


class BoardModel(models.Model):
    description = models.CharField(max_length=100, unique=True, verbose_name="Descrição")
    board_vendor = models.ForeignKey(BoardVendor, on_delete=models.CASCADE, verbose_name="Fabricante")

    objects = models.Manager()

    def __str__(self):
        return self.description


class ControlBoard(models.Model):
    PROTOTYPE_INTENSIVE_SIDE = 0
    PROTOTYPE_EXTENSIVE_SIDE = 1

    PrototypeSide = (
        (PROTOTYPE_INTENSIVE_SIDE, "Modelo Intensivo"),
        (PROTOTYPE_EXTENSIVE_SIDE, "Modelo Extensivo"),
    )

    nickname = models.CharField(max_length=50, unique=True, verbose_name="Apelido")
    mac_address = models.CharField(max_length=17, verbose_name='MAC address', unique=True,
                                   validators=[check_mac_address])
    prototype_side = models.IntegerField(verbose_name='Lado do modelo', choices=PrototypeSide)
    board_model = models.ForeignKey(BoardModel, on_delete=models.CASCADE, verbose_name="Modelo")

    objects = models.Manager()

    @property
    def prototype_side_description(self):
        return "{}".format(self.PrototypeSide[self.prototype_side][1])

    @property
    def short_mac_id(self):
        return self.mac_address[-5:-3] + self.mac_address[-2:]

    def __str__(self):
        return "{} - {}".format(self.nickname, self.prototype_side_description)


class ControlBoardEvent(models.Model):
    timestamp = models.DateTimeField()
    status_received = models.CharField(max_length=20, verbose_name="Valor lido")
    control_board = models.ForeignKey(ControlBoard, on_delete=models.CASCADE, verbose_name="Placa Controladora")

    objects = models.Manager()

    @property
    def status_translated(self):
        result = {}
        try:
            translation = BoardStatusInfo(str(self.status_received))
            return translation.to_dict
        except ValueError:
            pass
        return result

    def __str__(self):
        return "ControlBoard {} event received - timestamp: {}, status: {}".format(self.control_board.nickname,
                                                                                   self.timestamp,
                                                                                   self.status_received)


class SensorType(models.Model):
    sensor_type = models.CharField(max_length=50, verbose_name="Tipo")
    description = models.CharField(max_length=100, verbose_name="Descrição")
    data_sheet = models.TextField(verbose_name="Data sheet")
    precision = models.IntegerField(default=0, verbose_name="Precisão")

    objects = models.Manager()

    def __str__(self):
        return self.sensor_type


class Sensor(models.Model):
    ROLE_RAIN_DETECTION_SURFACE = 0
    ROLE_RAIN_DETECTION_DRAIN = 1
    ROLE_RAIN_ABSORPTION = 2
    ROLE_RAIN_AMOUNT = 3

    SensorRole = (
        (ROLE_RAIN_DETECTION_SURFACE, "Detecção de chuva na superfície"),
        (ROLE_RAIN_DETECTION_DRAIN, "Detecção de chuva no ralo"),
        (ROLE_RAIN_ABSORPTION, "Absorção de chuva"),
        (ROLE_RAIN_AMOUNT, "Quantidade de chuva"),
    )

    sensor_id = models.CharField(max_length=10, verbose_name="ID")
    description = models.CharField(max_length=100, verbose_name="Descrição")
    sensor_type = models.ForeignKey(SensorType, on_delete=models.CASCADE, verbose_name="Tipo")
    sensor_role = models.IntegerField(verbose_name='Função', choices=SensorRole)
    sensor_reading_conversion = models.FloatField(verbose_name="Conversão", default=0.0)
    control_board = models.ForeignKey(ControlBoard, on_delete=models.CASCADE, verbose_name="Placa Controladora")

    objects = models.Manager()

    @property
    def sensor_role_description(self):
        return "{}".format(self.SensorRole[self.sensor_role][1])

    def __str__(self):
        return "{} - {} - {}".format(self.control_board.nickname, self.sensor_id, self.sensor_role_description)


class SensorReadEvent(models.Model):
    timestamp = models.DateTimeField(verbose_name="Data/Hora")
    value_read = models.FloatField(verbose_name="Valor lido")
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, verbose_name="Sensor")

    objects = models.Manager()

    def __str__(self):
        return "Sensor {} read - timestamp: {}, value read: {}".format(self.sensor.sensor_id, self.timestamp,
                                                                       self.value_read)


class NotificationUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    notify_errors = models.BooleanField(default=False, verbose_name="Send errors notifications")

    objects = models.Manager()


class BoardStatusInfo:
    BOARD_STATUS_ARRAY_REGEX = "^[C,D,I,K,N,P,S,T,U,X][S][0,1,9]{3}[O,P][0-9]{1,4}[P][0-9]{1,2}[A][0-9]{1,5}$"

    PROCESS_RUNNING = 1
    PROCESS_STOPPED = 0

    RESET_BY_COMMAND = "C"
    RESET_BY_DISCONNECTION = "D"
    RESET_BY_KEEP_ALIVE = "K"
    RESET_BY_CANT_CONNECT = "X"
    RESET_BY_TIMEOUT_REGISTER = "T"
    RESET_BY_TIMEOUT_TIMESTAMP = "S"
    RESET_BY_UNABLE_CONNECT = "U"
    RESET_BY_INACTIVITY = "I"
    RESET_BY_PROCESS_STOPPED = "P"
    NORMAL_BOARD_STATUS = "N"

    MQTTSN_PROCESS = 0
    PUBLISH_PROCESS = 1
    CTRL_SUBSCRIPTION_PROCESS = 2
    WATCHDOG_PROCESS = 3
    REBOOT_PROCESS = 4
    GREEN_LED_PROCESS = 5
    RED_LED_PROCESS = 6
    REQUEST_TIMESTAMP_UPDATE_PROCESS = 7
    INTERRUPTION_SENSOR_RESET_INTERVAL_PROCESS = 8
    RAIN_SENSOR_DRAIN_PROCESS = 9
    MOISTURE_SENSOR_PROCESS = 10
    INTERRUPTION_SENSOR_PROCESS = 11
    REPORT_BOARD_GENERAL_STATUS_PROCESS = 12
    DETECT_TEST_MODE_PROCESS = 13

    ProcessNames = (
        (MQTTSN_PROCESS, "Processo MQTT-SN", PROCESS_RUNNING),
        (PUBLISH_PROCESS, "Processo de publish", PROCESS_STOPPED),
        (CTRL_SUBSCRIPTION_PROCESS, "Processo de controle de assinatura", PROCESS_STOPPED),
        (WATCHDOG_PROCESS, "Processo Watchdog", PROCESS_RUNNING),
        (REBOOT_PROCESS, "Processo de reboot", PROCESS_STOPPED),
        (GREEN_LED_PROCESS, "Processo de controle LED verde", PROCESS_RUNNING),
        (RED_LED_PROCESS, "Processo de controle LED vermelho", PROCESS_RUNNING),
        (REQUEST_TIMESTAMP_UPDATE_PROCESS, "Processo para requisição de atualização de data/hora", PROCESS_RUNNING),
        (INTERRUPTION_SENSOR_RESET_INTERVAL_PROCESS, "Processo de zeramentos dos sensores por interrupção", PROCESS_RUNNING),
        (RAIN_SENSOR_DRAIN_PROCESS, "Processo de leitura do sensor de ralo", PROCESS_RUNNING),
        (MOISTURE_SENSOR_PROCESS, "Processo de leitura do sensor de umidade", PROCESS_RUNNING),
        (INTERRUPTION_SENSOR_PROCESS, "Processo de leitura do sensor por interrupção", PROCESS_RUNNING),
        (REPORT_BOARD_GENERAL_STATUS_PROCESS, "Processo de reporte de status da controladora", PROCESS_RUNNING),
        (DETECT_TEST_MODE_PROCESS, "Processo de detecção do modo teste", PROCESS_STOPPED),
    )

    @staticmethod
    def bitfield(n: int):
        return [1 if digit == '1' else 0 for digit in bin(n)[2:]]

    @staticmethod
    def validate_board_status_array(data: str) -> bool:
        result = False
        pattern = re.compile(BoardStatusInfo.BOARD_STATUS_ARRAY_REGEX)
        if pattern.match(data):
            result = True
        return result

    def __init__(self, data: str):
        if len(data) >= 11:
            if BoardStatusInfo.validate_board_status_array(data):
                self._board_state = data[0]
                self._sensors_array = [0, 0, 0]
                for i in range(2, 5):
                    self._sensors_array[i - 2] = int(data[i])
                self._irq_events_count = int(data[6:data.find("P", 6)])
                self._process_count = int(data[data.find("P", 6) + 1:data.find("A", 7)])
                self._process_bitmap = int(data[data.find("A") + 1:])
            else:
                raise ValueError("Invalid status format. The string informed is not well formatted.")
        else:
            raise ValueError("Invalid status format. String size must be larger than 11 characters.")

    @property
    def board_state(self):
        result = "Indefinido"
        if self._board_state == BoardStatusInfo.NORMAL_BOARD_STATUS:
            result = "Normal"
        elif self._board_state == BoardStatusInfo.RESET_BY_COMMAND:
            result = "Reset por comando"
        elif self._board_state == BoardStatusInfo.RESET_BY_DISCONNECTION:
            result = "Reset por desconexão"
        elif self._board_state == BoardStatusInfo.RESET_BY_KEEP_ALIVE:
            result = "Reset por timeout keep alive"
        elif self._board_state == BoardStatusInfo.RESET_BY_CANT_CONNECT:
            result = "Reset por falha na conexão"
        elif self._board_state == BoardStatusInfo.RESET_BY_TIMEOUT_REGISTER:
            result = "Reset por timeout no registro"
        elif self._board_state == BoardStatusInfo.RESET_BY_TIMEOUT_TIMESTAMP:
            result = "Reset por timeout timestamp"
        elif self._board_state == BoardStatusInfo.RESET_BY_UNABLE_CONNECT:
            result = "Reset impossível conectar"
        elif self._board_state == BoardStatusInfo.RESET_BY_INACTIVITY:
            result = "Reset por inatividade"
        elif self._board_state == BoardStatusInfo.RESET_BY_PROCESS_STOPPED:
            result = "Reset por parada de proceso"
        return result

    @property
    def sensors_state_array(self):
        result = ["U", "U", "U"]
        for i in range(2, 5):
            result[i - 2] = "O" if self._sensors_array[i - 2] == 0 else "D" if self._sensors_array[
                                                                                     i - 2] == 1 else "E"
        return result

    @property
    def irq_events_count(self):
        return self._irq_events_count

    @property
    def board_process_count(self):
        return self._process_count

    @property
    def board_process_bitmap(self):
        result = []
        bitmap = BoardStatusInfo.bitfield(self._process_bitmap)
        for i in range(0, 14):
            process = {"name": BoardStatusInfo.ProcessNames[i][1],
                       "state": "E" if BoardStatusInfo.ProcessNames[i][2] != bitmap[i]
                       else "X" if bitmap[i] == BoardStatusInfo.PROCESS_RUNNING else "P"}
            result.append(process)
        return result

    @property
    def to_dict(self):
        return {"board_state": self.board_state,
                "sensors_state_array": self.sensors_state_array,
                "irq_events_count": self.irq_events_count,
                "board_process_count": self.board_process_count,
                "board_process_bitmap": self.board_process_bitmap
                }
