from datetime import datetime

from django.utils import timezone
from django.db.models import Q

from model.models import SensorReadEvent, ControlBoard, Sensor


def get_diff_datetime(start_timestamp, end_timestamp):
    dt_start = timezone.localtime(start_timestamp)
    dt_end = timezone.localtime(end_timestamp)
    diff = dt_end - dt_start
    hours = ("0" + str((diff.days * 24) + ((diff.seconds // 60) // 60)))[-2:]
    minutes = ("0" + str((diff.seconds // 60) % 60))[-2:]
    seconds = ("0" + str(diff.seconds % 60))[-2:]
    result = hours + ":" + minutes + ":" + seconds
    return result


def get_peak_delay(start_date_filter: str = None, end_date_filter: str = None):
    query_res = SensorReadEvent.objects.all().order_by('timestamp')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_lte=end_dt)
    boards = ControlBoard.objects.all()
    result = []
    for board in boards:
        query_events = query_res.filter(Q(sensor__control_board_id=board.id) & (
                Q(sensor__sensor_role=Sensor.ROLE_RAIN_DETECTION_SURFACE) |
                Q(sensor__sensor_role=Sensor.ROLE_RAIN_DETECTION_DRAIN)))
        start_time = None
        for event in query_events:
            if not start_time and event.sensor.sensor_role == Sensor.ROLE_RAIN_DETECTION_SURFACE:
                start_time = event.timestamp
            if start_time and event.sensor.sensor_role == Sensor.ROLE_RAIN_DETECTION_DRAIN:
                diff = get_diff_datetime(start_time, event.timestamp)
                surface_rain_timestamp = timezone.localtime(start_time).strftime('%d/%m/%Y %H:%M:%S')
                drain_rain_timestamp = timezone.localtime(event.timestamp).strftime('%d/%m/%Y %H:%M:%S')
                result.append(
                    {"prototype_side": board.prototype_side_description,
                     "surface_rain_timestamp": surface_rain_timestamp,
                     "drain_rain_timestamp": drain_rain_timestamp, "diff": diff})
                start_time = None
    return result


def get_pluviometer_reading(start_date_filter: str = None, end_date_filter: str = None):
    query_res = SensorReadEvent.objects.all().order_by('timestamp')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_lte=end_dt)
    boards = ControlBoard.objects.all()
    result = []
    for board in boards:
        query_events = query_res.filter(Q(sensor__control_board_id=board.id) & (
            Q(sensor__sensor_role=Sensor.ROLE_RAIN_AMOUNT)))
        for event in query_events:
            timestamp = timezone.localtime(event.timestamp).strftime('%d/%m/%Y %H:%M:%S')
            value_converted = (event.sensor.sensor_reading_conversion * event.value_read)
            result.append(
                {"sensor_id": event.sensor.sensor_id, "timestamp": timestamp, "pluviometer_count": value_converted})
    return result
