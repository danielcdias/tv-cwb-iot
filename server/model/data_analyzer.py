import logging

from datetime import datetime
from pytz import timezone as tz
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from model.models import SensorReadEvent, ControlBoard, Sensor
from copy import deepcopy

DAYS_FOR_NEXT_PEAK_DELAY = 3
RAIN_QUANTITY_SENSOR_RESET_INTERVAL_IN_MINUTES = 15

calibration_tables = []

logger = logging.getLogger("tvcwb")


def get_float_as_str_with_comma(number: float, decimals: int) -> str:
    return ("{:.{dec}f}".format(number, dec=decimals)).replace(".", ",")


def get_peak_delay(start_date_filter: str = None, end_date_filter: str = None) -> list:
    result = []
    query_res = SensorReadEvent.objects.all().filter(sensor__active=True).order_by('timestamp')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(init_dt):
            init_dt = timezone.make_aware(init_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(end_dt):
            end_dt = timezone.make_aware(end_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__lte=end_dt)
    query_rds = query_res.filter(sensor__sensor_role=Sensor.ROLE_RAIN_DETECTION_SURFACE)
    rain_events = []
    started = False
    last_value_read = 0
    current_start = None
    rain_event = {}
    for soc_event in query_rds:
        if not started and soc_event.value_read > 0:
            started = True
            current_start = soc_event
        elif started and soc_event.value_read < last_value_read:
            rain_event['started'] = current_start.timestamp
            rain_event['ended'] = soc_event.timestamp
            rain_events.append(deepcopy(rain_event))
            started = False
        last_value_read = soc_event.value_read
    current_peak = None
    peak_delays_found = []
    delay = DAYS_FOR_NEXT_PEAK_DELAY
    for peak_delay in rain_events:
        if current_peak:
            td = peak_delay['started'] - current_peak['ended']
            diff = (td.days + (td.seconds / 86400))
            if diff >= delay:
                peak_delays_found.append(peak_delay)
                delay = DAYS_FOR_NEXT_PEAK_DELAY
                current_peak = peak_delay
            else:
                current_peak['ended'] = peak_delay['ended']
        if not current_peak:
            current_peak = peak_delay
            peak_delays_found.append(peak_delay)
    boards = ControlBoard.objects.all()
    query_rdd = query_res.filter(sensor__sensor_role=Sensor.ROLE_RAIN_DETECTION_DRAIN)
    for board in boards:
        for i in range(0, len(peak_delays_found)):
            current_peak = peak_delays_found[i]['started']
            next_peak = peak_delays_found[i + 1]['started'] if (i + 1) < len(peak_delays_found) else None
            query_rdd_board_event = query_rdd.filter(sensor__control_board_id=board.id).filter(
                timestamp__gte=current_peak)
            if next_peak:
                query_rdd_board_event = query_rdd_board_event.filter(sensor__control_board_id=board.id).filter(
                    timestamp__lt=next_peak)
            if query_rdd_board_event:
                peak_delay_event = {'prototype_side': board.prototype_side_description,
                                    'start': timezone.localtime(current_peak).strftime(settings.DATETIME_FORMAT),
                                    'end': timezone.localtime(query_rdd_board_event[0].timestamp).strftime(
                                        settings.DATETIME_FORMAT),
                                    'diff': _get_diff_datetime(current_peak, query_rdd_board_event[0].timestamp)}
                result.append(deepcopy(peak_delay_event))
    if result:
        result.sort(key=lambda item: (datetime.strptime(item.get("start"), settings.DATETIME_FORMAT),
                                      datetime.strptime(item.get("end"), settings.DATETIME_FORMAT)))
    return result


def get_pluviometer_rain_events(start_date_filter: str = None, end_date_filter: str = None) -> list:
    query_res = SensorReadEvent.objects.all().filter(
        Q(sensor__active=True) & Q(sensor__sensor_role=Sensor.ROLE_RAIN_AMOUNT)).order_by('timestamp', 'value_read')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(init_dt):
            init_dt = timezone.make_aware(init_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(end_dt):
            end_dt = timezone.make_aware(end_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__lte=end_dt)
    boards = ControlBoard.objects.all()
    result = []
    prototype_areas = []
    for board in boards:
        prototype_areas.append(
            {"prototype_side": board.prototype_side_description, "prototype_area": board.prototype_area})

    rain_events = []
    for i in range(0, len(query_res)):
        save_event = False
        if (i + 1) < len(query_res):
            td = query_res[i + 1].timestamp - query_res[i].timestamp
            diff = ((td.days * 1440) + (td.seconds / 60))
            if (query_res[i].value_read > query_res[i + 1].value_read) or (
                    (diff > RAIN_QUANTITY_SENSOR_RESET_INTERVAL_IN_MINUTES) and (query_res[i].value_read > 0)):
                save_event = True
        elif query_res[i].value_read > 0:
            save_event = True
        if save_event:
            timestamp = timezone.localtime(query_res[i].timestamp).strftime(settings.DATETIME_FORMAT)
            value_converted = (query_res[i].sensor.sensor_reading_conversion * query_res[i].value_read)
            entry = {"sensor_id": query_res[i].sensor.sensor_id, "timestamp": timestamp,
                     "pluviometer_count": value_converted}
            for area in prototype_areas:
                entry[area['prototype_side']] = float(area['prototype_area']) * value_converted
            rain_events.append(entry)

    sum_plv = 0
    for i in range(0, len(rain_events)):
        save_event = False
        if (i + 1) < len(rain_events):
            if rain_events[i]['timestamp'][0:10] != rain_events[i + 1]['timestamp'][0:10]:
                save_event = True
        else:
            save_event = True
        sum_plv += rain_events[i]['pluviometer_count']
        if save_event:
            date = rain_events[i]['timestamp'][0:10]
            day_event = {"sensor_id": rain_events[i]['sensor_id'], "date": date,
                         "pluviometer_sum": get_float_as_str_with_comma(sum_plv, 4)}
            for area in prototype_areas:
                day_event[area['prototype_side']] = get_float_as_str_with_comma(
                    float(area['prototype_area']) * sum_plv, 4)
            result.append(day_event)
            sum_plv = 0

    return result


def get_absorption_readings(start_date_filter: str = None, end_date_filter: str = None) -> list:
    query_res = SensorReadEvent.objects.all().filter(
        Q(sensor__active=True) & Q(sensor__sensor_role=Sensor.ROLE_RAIN_ABSORPTION) & Q(value_read__gt=0)).order_by(
        'timestamp', 'value_read')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(init_dt):
            init_dt = timezone.make_aware(init_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(end_dt):
            end_dt = timezone.make_aware(end_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__lte=end_dt)
    result = []
    for event in query_res:
        translated_event = {"prototype_side": event.sensor.control_board.prototype_side_description,
                            "timestamp": timezone.localtime(event.timestamp).strftime(settings.DATETIME_FORMAT),
                            "water_absorbed": get_float_as_str_with_comma(_get_absorption_translation(event), 2)}
        result.append(translated_event)
    return result


def get_temperature_readings(start_date_filter: str = None, end_date_filter: str = None) -> list:
    query_res = SensorReadEvent.objects.all().filter(
        Q(sensor__active=True) & Q(sensor__sensor_role=Sensor.ROLE_TEMPERATURE)).order_by('timestamp')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(init_dt):
            init_dt = timezone.make_aware(init_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, settings.DATETIME_FORMAT)
        if not timezone.is_aware(end_dt):
            end_dt = timezone.make_aware(end_dt, tz(settings.TIME_ZONE))
        query_res = query_res.filter(timestamp__lte=end_dt)
    result = []
    if query_res:
        boards = ControlBoard.objects.all()
        for board in boards:
            query_board = query_res.filter(sensor__control_board_id=board.id)
            same_hour_events = []
            for i in range(0, len(query_board)):
                current_event = query_board[i]
                current_date = timezone.localtime(current_event.timestamp).strftime(settings.DATE_FORMAT)
                current_hour = timezone.localtime(current_event.timestamp).strftime('%H')
                same_hour_events.append(current_event)
                save_event = False
                if (i + 1) < len(query_board):
                    next_event = query_board[i + 1]
                    next_date = timezone.localtime(next_event.timestamp).strftime(settings.DATE_FORMAT)
                    next_hour = timezone.localtime(next_event.timestamp).strftime('%H')
                    if (current_date != next_date) or (current_hour != next_hour):
                        save_event = True
                else:
                    save_event = True
                if save_event:
                    result.append(_get_avg_temperature(same_hour_events, current_date, current_hour))
                    same_hour_events = []
    result.sort(key=lambda x: (x['date'][6:10], x['date'][3:5], x['date'][0:2], x['hour']))
    return result


def _get_avg_temperature(events: list, date_str: str, hour_str: str) -> dict:
    sum_evt = 0
    prototype_side = events[0].sensor.control_board.prototype_side_description
    for e in events:
        sum_evt += e.value_read
    avg_value = sum_evt / len(events)
    tmp_event = {"prototype_side": prototype_side,
                 "date": date_str,
                 "hour": hour_str,
                 "temperature": get_float_as_str_with_comma(avg_value, 2)}
    return tmp_event


def _get_diff_datetime(start_timestamp, end_timestamp) -> str:
    dt_start = timezone.localtime(start_timestamp)
    dt_end = timezone.localtime(end_timestamp)
    diff = dt_end - dt_start
    hours = ("0" + str((diff.days * 24) + ((diff.seconds // 60) // 60)))[-2:]
    minutes = ("0" + str((diff.seconds // 60) % 60))[-2:]
    seconds = ("0" + str(diff.seconds % 60))[-2:]
    result = hours + ":" + minutes + ":" + seconds
    return result


def _init_calibration_tables():
    global calibration_tables
    absorption_sensors = Sensor.objects.filter(sensor_role=Sensor.ROLE_RAIN_ABSORPTION)
    for sensor in absorption_sensors:
        calibration_table = {'nickname': sensor.control_board.nickname, 'sensor_id': sensor.sensor_id,
                             'calibration_table':
                                 sensor.sensorcalibrationinterval_set.all().order_by('-interval_floor_value')}
        calibration_tables.append(calibration_table)


def _get_absorption_translation(sensor_reading: SensorReadEvent) -> float:
    if sensor_reading.sensor.sensor_role != Sensor.ROLE_RAIN_ABSORPTION:
        raise TypeError("The informed sensor reading event is not from a rain absorption role sensor.")
    if not calibration_tables:
        _init_calibration_tables()
    calibration_table = []
    for c in calibration_tables:
        if c['nickname'] == sensor_reading.sensor.control_board.nickname and \
                c['sensor_id'] == sensor_reading.sensor.sensor_id:
            calibration_table = c['calibration_table']
            break
    percentage_selected = 0.0
    for interval in calibration_table:
        if sensor_reading.value_read > interval.interval_floor_value:
            break
        percentage_selected = interval.water_percentage
    result = sensor_reading.sensor.control_board.prototype_weight * (percentage_selected / 100)
    return result
