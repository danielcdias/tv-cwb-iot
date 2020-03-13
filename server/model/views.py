import csv
import json
import logging
import calendar

from datetime import timedelta, datetime

from django.utils import timezone
from django.http import StreamingHttpResponse
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

CHART_LINE_STYLES = [['#ff0000', 'triangle'], ['#0000ff', 'circle'], ['#00ff00', 'rect'], ['#ffff00', 'cross'],
                     ['#ffa500', 'star'], ['#ff00ff', 'rectRounded'], ['#00ffff', 'crossRot'], ['#a5a5a5', 'rectRot']]


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
            td = end_dt - init_dt
            diff = (td.days + (td.seconds / 86400))
            if diff > 365:
                still_valid = False
                form.add_error('end_timestamp', "O intervalo de dados não deve ser maior que 1 ano.")
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
    return render(request, 'model/index.html',
                  {"form": form,
                   "start_timestamp": request.POST['start_timestamp'] if 'start_timestamp' in request.POST else '',
                   "end_timestamp": request.POST['end_timestamp'] if 'end_timestamp' in request.POST else ''})


def get_temperature_info(request):
    logger.debug("get_temperature_info starting - request.POST: {}".format(request.POST))
    chart_type_by_date = True if 'chart_type' not in request.POST else (
        True if request.POST['chart_type'] == 'date' else False)
    dates_available = request.POST['dates_available'][1:-1].replace('\'', '').split(
        ', ') if 'dates_available' in request.POST else []
    months_available = request.POST['months_available'][1:-1].replace('\'', '').split(
        ', ') if 'months_available' in request.POST else []
    date_selected = request.POST['date_selected'] if 'date_selected' in request.POST else ''
    month_selected = request.POST['month_selected'] if 'month_selected' in request.POST else ''
    data_selected = []
    # Define date/time interval
    init_dt = request.POST['start_timestamp']
    end_dt = request.POST['end_timestamp']
    if chart_type_by_date and date_selected:
        init_dt = date_selected + " 00:00"
        end_dt = date_selected + " 23:00"
    elif not chart_type_by_date and month_selected:
        init_dt = "01/" + month_selected + " 00:00"
        end_dt = _get_end_date_from_month_for_query(month_selected)
    logger.debug("init_dt: {}, end_dt: {}".format(init_dt, end_dt))
    data = analyzer.get_temperature_readings(start_date_filter=init_dt, end_date_filter=end_dt)
    if data:
        # Load dates available and/or months_available, if not informed
        if not dates_available:
            for x in data:
                if x['date'] not in dates_available:
                    dates_available.append(x['date'])
        if not months_available:
            for x in data:
                if x['date'][3:] not in months_available:
                    months_available.append(x['date'][3:])
        # Define date or month selected if not informed
        if chart_type_by_date:
            if not date_selected and dates_available:
                date_selected = dates_available[-1]
        else:
            if not month_selected and months_available:
                month_selected = months_available[-1]
        # Load data from the date or month selected, if dates available
        if chart_type_by_date:
            if dates_available:
                for x in data:
                    if x['date'] == date_selected:
                        data_selected.append(x)
        else:
            if months_available:
                data_filtered = []
                for x in data:
                    if x['date'][3:] == month_selected:
                        data_filtered.append(x)
                for ps in ControlBoard.PrototypeSide:
                    for h in range(0, 23):
                        sum_temp = 0
                        gen = ([x for x in data_filtered if int(x['hour']) == h and x['prototype_side'] == ps[1]])
                        data_count = 0;
                        for x in gen:
                            sum_temp += float(x['temperature'].replace(',', '.'))
                            data_count += 1
                        data_selected.append({"prototype_side": ps[1],
                                              "date": month_selected,
                                              "hour": str(h).zfill(2),
                                              "temperature": analyzer.get_float_as_str_with_comma(
                                                  (sum_temp / data_count),
                                                  2)})
        # Calculate the min and max temperatures for each prototype side
        thermal_amplitude = []
        for ps in ControlBoard.PrototypeSide:
            max_temp_ps = -999
            min_temp_ps = 999
            data_selected_ps = ([a for a in data_selected if a['prototype_side'] == ps[1]])
            for x in data_selected_ps:
                temperature = float(x['temperature'].replace(',', '.'))
                if temperature > max_temp_ps:
                    max_temp_ps = temperature
                if temperature < min_temp_ps:
                    min_temp_ps = temperature
            thermal_amplitude.append(
                {"prototype_side": ps[1], "max_temp": analyzer.get_float_as_str_with_comma(max_temp_ps, 2),
                 "min_temp": analyzer.get_float_as_str_with_comma(min_temp_ps, 2),
                 "amplitude": analyzer.get_float_as_str_with_comma(max_temp_ps - min_temp_ps, 2)})
        # Load datasets and labels
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
                    {"label": x['prototype_side'], "data": [temperature], "fill": False, "lineTension": 0.01,
                     "backgroundColor": CHART_LINE_STYLES[color_index][0],
                     "borderColor": CHART_LINE_STYLES[color_index][0],
                     "pointStyle": CHART_LINE_STYLES[color_index][1],
                     "pointBorderWidth": 4})
                color_index += 1
            else:
                dts_index = next((index for (index, d) in enumerate(datasets) if d["label"] == x['prototype_side']),
                                 None)
                datasets[dts_index]['data'].append(temperature)
            if x['hour'] not in labels:
                labels.append(x['hour'])
        data = {"labels": labels, "datasets": datasets}
        # Define minimum and maximum ticks for y axis
        min_tick = int(min_temp)
        max_tick = int(max_temp) + 1
        step_size = 1 if (max_temp - min_temp) <= 10 else 2
        if ((min_tick % 2) == 0 and (max_tick % 2) != 0) or ((min_tick % 2) != 0 and (max_tick % 2) == 0):
            min_tick -= 1
        # Defining chart title
        chart_title = "Variação da temperatura medida nos modelos, por hora, em {}".format(date_selected) if \
            chart_type_by_date else "Média de temperatura medida nos modelos, por hora, no mês de {}".format(
            month_selected)
        result = {"dates_available": dates_available, "months_available": months_available,
                  "date_selected": date_selected, "month_selected": month_selected,
                  "data": json.dumps(data), "max_tick": max_tick, "min_tick": min_tick, "step_size": step_size,
                  "thermal_amplitude": thermal_amplitude, "chart_title": chart_title,
                  "start_timestamp": request.POST['start_timestamp'], "end_timestamp": request.POST['end_timestamp']}
    else:
        result = {"dates_available": [], "months_available": [], "date_selected": "", "month_selected": "",
                  "data": [], "max_tick": 0, "min_tick": 0, "step_size": 0,
                  "thermal_amplitude": [], "chart_title": "", "start_timestamp": request.POST['start_timestamp'],
                  "end_timestamp": request.POST['end_timestamp']}
    logger.debug("get_temperature_info result: {}:".format(result))
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


def _get_end_date_from_month_for_query(month_selected: str):
    month = int(month_selected[0:2])
    year = int(month_selected[3:])
    last_day = calendar.monthrange(year, month)[1]
    dt = datetime(year, month, last_day)
    str_date = dt.strftime("%d/%m/%Y")
    return str_date + " 23:59"
