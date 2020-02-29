import logging

from datetime import datetime, timedelta

from django.utils import timezone
from django.conf import settings
from django.db.models import Q, Sum, Value as V
from django.db.models.functions import TruncDay, Coalesce

from model.models import SensorReadEvent, ControlBoard, Sensor
from copy import deepcopy

DAYS_FOR_NEXT_PEAK_DELAY = 3
RAIN_QUANTITY_SENSOR_RESET_INTERVAL_IN_MINUTES = 15

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
    result = []
    query_res = SensorReadEvent.objects.all().filter(sensor__active=True).order_by('timestamp')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_lte=end_dt)
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
                timestamp__gt=current_peak)
            if next_peak:
                query_rdd_board_event = query_rdd.filter(sensor__control_board_id=board.id).filter(
                    timestamp__lt=next_peak)
            if query_rdd_board_event:
                peak_delay_event = {'prototype_side': board.prototype_side_description,
                                    'start': timezone.localtime(current_peak).strftime('%d/%m/%Y %H:%M:%S'),
                                    'end': timezone.localtime(query_rdd_board_event[0].timestamp).strftime(
                                        '%d/%m/%Y %H:%M:%S'),
                                    'diff': get_diff_datetime(current_peak, query_rdd_board_event[0].timestamp)}
                result.append(deepcopy(peak_delay_event))
    if result:
        result.sort(key=lambda item: (datetime.strptime(item.get("start"), '%d/%m/%Y %H:%M:%S'),
                                      datetime.strptime(item.get("end"), '%d/%m/%Y %H:%M:%S')))
    return result


def get_pluviometer_reading(start_date_filter: str = None, end_date_filter: str = None):
    query_res = SensorReadEvent.objects.all().filter(
        Q(sensor__active=True) & Q(sensor__sensor_role=Sensor.ROLE_RAIN_AMOUNT)).order_by('timestamp', 'value_read')
    if start_date_filter:
        init_dt = datetime.strptime(start_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_gte=init_dt)
    if end_date_filter:
        end_dt = datetime.strptime(end_date_filter, '%Y-%m-%dT%H-%M-%S')
        query_res = query_res.filter(timestamp_lte=end_dt)
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
            timestamp = timezone.localtime(query_res[i].timestamp).strftime('%d/%m/%Y %H:%M:%S')
            value_converted = (query_res[i].sensor.sensor_reading_conversion * query_res[i].value_read)
            entry = {"sensor_id": query_res[i].sensor.sensor_id, "timestamp": timestamp,
                     "pluviometer_count": value_converted}
            for area in prototype_areas:
                entry[area['prototype_side']] = area['prototype_area'] * value_converted
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
                    area['prototype_area'] * sum_plv, 4)
            result.append(day_event)
            sum_plv = 0

    return result


def get_float_as_str_with_comma(number: float, decimals: int) -> str:
    return ("{:.{dec}f}".format(number, dec=decimals)).replace(".", ",")
