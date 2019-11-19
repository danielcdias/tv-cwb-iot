import django_tables2 as tables
from .models import SensorReadEvent, ControlBoardEvent


class SensorsReadingTable(tables.Table):
    value_read = tables.Column(attrs={"td": {"align": "right"}})

    class Meta:
        model = SensorReadEvent
        template_name = "django_tables2/bootstrap.html"
        fields = ("sensor.sensor_id", "sensor.description", "timestamp", "value_read",
                  "sensor.control_board.prototype_side",)


class ControlBoardReadingTable(tables.Table):
    class Meta:
        model = ControlBoardEvent
        template_name = "django_tables2/bootstrap.html"
        fields = ("control_board.nickname", "control_board.prototype_side", "timestamp", "status_received",)
