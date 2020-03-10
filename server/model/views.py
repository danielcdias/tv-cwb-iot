import csv
import json
import logging

from datetime import timedelta, datetime

from django.utils import timezone
from django.http import StreamingHttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.conf import settings

from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from .models import SensorReadEvent, ControlBoardEvent, ControlBoard, BoardStatusInfo
from model import data_analyzer as analyzer
from model.tables import SensorsReadingTable, ControlBoardReadingTable
from model.filters import SensorReadEventFilter, ControlBoardEventFilter
from model.forms import DataAvailable

logger = logging.getLogger("tvcwb")

# CHART_COLORS = ['red', 'blue', 'green', 'yellow', 'orange', 'purple']
CHART_COLORS = ['#ff0000', '#0000ff', '#00ff00', '#ffff00', '#ffa500', '#ff00ff', '#00ffff', '#a5a5a5']


class SensorsView(SingleTableMixin, FilterView):
    model = SensorReadEvent
    table_class = SensorsReadingTable
    template_name = "model/sensors.html"
    filterset_class = SensorReadEventFilter
    queryset = SensorReadEvent.objects.all().filter(sensor__active=True).order_by('-timestamp')


class ControlBoardEventsView(SingleTableMixin, FilterView):
    model = ControlBoardEvent
    table_class = ControlBoardReadingTable
    template_name = "model/control_board.html"
    filterset_class = ControlBoardEventFilter
    queryset = ControlBoardEvent.objects.all().order_by('-timestamp')
    context_object_name = "control_boards"

    def get_context_data(self, **kwargs):
        context = super(ControlBoardEventsView, self).get_context_data(**kwargs)
        context['last_status_array'] = ControlBoardEventsView.last_status_array()
        context['process_bitmap_tooltips'] = ControlBoardEventsView.process_bitmap_tooltips()
        return context

    @staticmethod
    def last_status_array():
        result = []
        boards = ControlBoard.objects.all()
        for board in boards:
            query_status_array = board.controlboardevent_set.filter(
                status_received__iregex=BoardStatusInfo.BOARD_STATUS_ARRAY_REGEX).order_by(
                '-timestamp')
            query_fwv = board.controlboardevent_set.filter(
                status_received__startswith="FWV").order_by(
                '-timestamp')
            query_last_start = board.controlboardevent_set.filter(
                status_received__startswith="STT").order_by(
                '-timestamp')
            query_last_tur = board.controlboardevent_set.filter(
                status_received__startswith="TUR").order_by(
                '-timestamp')
            count_reset_l7d = board.controlboardevent_set.filter(
                timestamp__gte=(timezone.now() - timedelta(days=7))).filter(status_received="STT").order_by(
                '-timestamp')
            count_tur_l7d = board.controlboardevent_set.filter(
                timestamp__gte=(timezone.now() - timedelta(days=7))).filter(status_received="TUR").order_by(
                '-timestamp')
            board_data = {"board": board.nickname, "info_array": {}, "firmware_version": "", "last_start": "",
                          "last_tur": "", "resets_count": 0, "tur_count": 0}
            if query_status_array:
                board_data["info_array"] = query_status_array[0].status_translated
            if query_fwv:
                board_data["firmware_version"] = query_fwv[0].status_received[3:]
            if query_last_start:
                board_data["last_start"] = timezone.localtime(query_last_start[0].timestamp).strftime(
                    settings.DATETIME_FORMAT)
            if query_last_tur:
                board_data["last_tur"] = timezone.localtime(query_last_tur[0].timestamp).strftime(
                    settings.DATETIME_FORMAT)
            if count_reset_l7d:
                board_data["resets_count"] = len(count_reset_l7d)
            if count_tur_l7d:
                board_data["tur_count"] = len(count_tur_l7d)

            result.append(board_data)
        return result

    @staticmethod
    def process_bitmap_tooltips():
        result = []
        for name in BoardStatusInfo.ProcessNames:
            result.append(
                name[1] + ". Deve estar " + ("executando" if name[2] == BoardStatusInfo.PROCESS_RUNNING else "parado"))
        return result


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def get_sensors_read_event_in_csv(request):
    sensors_read_events = SensorReadEvent.objects.all().filter(sensor__active=True).order_by('timestamp')
    rows = [['Modelo', 'ID do Sensor', 'Timestamp', 'Valor Lido']]
    for sensor_read in sensors_read_events:
        dt = timezone.localtime(sensor_read.timestamp).strftime(settings.DATETIME_FORMAT)
        value_read = str(sensor_read.value_read).replace('.', ',') if request.GET.get('sep') == 'sc' else str(
            sensor_read.value_read)
        rows.append(
            [sensor_read.sensor.control_board.prototype_side_description, sensor_read.sensor.sensor_id, dt, value_read])

    return _generate_csv('senso_read_events.csv', rows, request)


def get_peak_delay_in_csv(request):
    start_date_filter = request.GET.get('start') if request.GET.get('start') else None
    end_date_filter = request.GET.get('end') if request.GET.get('end') else None
    results = analyzer.get_peak_delay(start_date_filter=start_date_filter, end_date_filter=end_date_filter)
    rows = [['Modelo', 'Data/Hora Detecçao Superfície', 'Data/Hora Detecção Ralo', 'Diferença']]
    for result in results:
        rows.append([result['prototype_side'], result['start'], result['end'],
                     result['diff']])

    return _generate_csv('atraso_de_pico.csv', rows, request)


def get_pluviometer_rain_events_in_csv(request):
    start_date_filter = request.GET.get('start') if request.GET.get('start') else None
    end_date_filter = request.GET.get('end') if request.GET.get('end') else None
    results = analyzer.get_pluviometer_rain_events(start_date_filter=start_date_filter, end_date_filter=end_date_filter)
    rows = [['Sensor', 'Data', 'Precipitação em litros']]
    if results:
        keys = list(results[0].keys())
        for i in range(3, len(keys)):
            rows[0].append(keys[i])
    for result in results:
        entry = [result['sensor_id'], result['date'], result['pluviometer_sum']]
        for i in range(3, len(result)):
            entry.append(result[rows[0][i]])
        rows.append(entry)
    return _generate_csv('pluviometro.csv', rows, request)


def get_absorption_readings_in_csv(request):
    start_date_filter = request.GET.get('start') if request.GET.get('start') else None
    end_date_filter = request.GET.get('end') if request.GET.get('end') else None
    results = analyzer.get_absorption_readings(start_date_filter=start_date_filter, end_date_filter=end_date_filter)
    rows = [['Modelo', 'Data/Hora', 'Água absorvida (litros)']]
    for result in results:
        entry = [result['prototype_side'], result['timestamp'], result['water_absorbed']]
        rows.append(entry)
    return _generate_csv('absorção-água.csv', rows, request)


def get_temperature_readings_in_csv(request):
    start_date_filter = request.GET.get('start') if request.GET.get('start') else None
    end_date_filter = request.GET.get('end') if request.GET.get('end') else None
    results = analyzer.get_temperature_readings(start_date_filter=start_date_filter, end_date_filter=end_date_filter)
    rows = [['Modelo', 'Data', 'Hora', 'Temperatura (°C)']]
    for result in results:
        entry = [result['prototype_side'], result['date'], result['hour'], result['temperature']]
        rows.append(entry)
    return _generate_csv('temperatura.csv', rows, request)


def _generate_csv(csv_filname: str, rows, request):
    sep = ';' if request.GET.get('sep') == 'sc' else ','
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer, delimiter=sep, quotechar='"', quoting=csv.QUOTE_ALL)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                     content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="' + csv_filname + '"'
    return response


def form_data_available(request):
    form = DataAvailable(request.POST) if request.method == 'POST' else DataAvailable()
    if form.is_valid():
        still_valid = True
        if request.POST['start_timestamp'] and request.POST['end_timestamp']:
            init_dt = datetime.strptime(request.POST['start_timestamp'], settings.DATETIME_FORMAT)
            end_dt = datetime.strptime(request.POST['end_timestamp'], settings.DATETIME_FORMAT)
            if init_dt >= end_dt:
                still_valid = False
                form.add_error('end_timestamp', "A data/hora final deve ser maior que a inicial.")
        if still_valid:
            option_selected = int(request.POST['data_type'])
            if option_selected == DataAvailable.DATA_TEMPERATURE:
                return get_temperature_info(request)
            elif option_selected == DataAvailable.DATA_PLUVIOMETER:
                return get_pluviometer_info(request)
            elif option_selected == DataAvailable.DATA_PEAK_DELAY:
                return get_peak_delay_info(request)
            elif option_selected == DataAvailable.DATA_WATER_ABSORPTION:
                return get_water_absorption_info(request)
    return render(request, 'model/index.html', {'form': form})


def get_temperature_info(request):
    logger.debug("request.POST: {}".format(request.POST))
    dates_available = request.POST['dates_available'][1:-1].replace('\'', '').split(
        ', ') if 'dates_available' in request.POST else []
    date_selected = request.POST['date_selected'] if 'date_selected' in request.POST else ''
    data_selected = []
    init_dt = date_selected + " 00:00" if date_selected else request.POST['start_timestamp']
    end_dt = date_selected + " 23:59" if date_selected else request.POST['end_timestamp']
    data = analyzer.get_temperature_readings(start_date_filter=init_dt, end_date_filter=end_dt)
    if not dates_available:
        for x in data:
            if x['date'] not in dates_available:
                dates_available.append(x['date'])
    if not date_selected and dates_available:
        date_selected = dates_available[-1]
    if dates_available:
        for x in data:
            if x['date'] == date_selected:
                data_selected.append(x)
    labels = []
    datasets = []
    color_index = 0
    max_temp = -999
    min_temp = 999
    for x in data_selected:
        temperature = float(x['temperature'].replace(',', '.'))
        if temperature > max_temp:
            max_temp = temperature
        if temperature < min_temp:
            min_temp = temperature
        if not any(a['label'] == x['prototype_side'] for a in datasets):
            datasets.append(
                {"label": x['prototype_side'], "data": [temperature], "fill": False,
                 "backgroundColor": CHART_COLORS[color_index],
                 "borderColor": CHART_COLORS[color_index]})
            color_index += 1
        else:
            dts_index = next((index for (index, d) in enumerate(datasets) if d["label"] == x['prototype_side']), None)
            datasets[dts_index]['data'].append(temperature)
        if x['hour'] not in labels:
            labels.append(x['hour'])
    data = {"labels": labels, "datasets": datasets}
    min_tick = (int(min_temp) - 1)
    max_tick = (int(max_temp) + 1)
    step_size = 1 if (max_temp - min_temp) <= 10 else 2
    if ((min_tick % 2) == 0 and (max_tick % 2) != 0) or ((min_tick % 2) != 0 and (max_tick % 2) == 0):
        min_tick -= 1
    result = {"dates_available": dates_available, 'date_selected': date_selected, 'data': json.dumps(data),
              'max_tick': max_tick, 'min_tick': min_tick, 'step_size': step_size}
    logger.debug("Result: {}:".format(result))
    return render(request, 'model/temperature_info.html', result)


def get_pluviometer_info(request):
    # TODO Implementar
    return render(request, 'model/not_implemented.html')


def get_peak_delay_info(request):
    # TODO Implementar
    return render(request, 'model/not_implemented.html')


def get_water_absorption_info(request):
    # TODO Implementar
    return render(request, 'model/not_implemented.html')
