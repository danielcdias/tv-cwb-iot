import csv

from django.utils import timezone
from django.http import StreamingHttpResponse

from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from .models import SensorReadEvent, ControlBoardEvent
from model import data_analyzer as analyzer
from model.tables import SensorsReadingTable, ControlBoardReadingTable
from model.filters import SensorReadEventFilter, ControlBoardEventFilter


class IndexView(SingleTableMixin, FilterView):
    model = SensorReadEvent
    table_class = SensorsReadingTable
    template_name = "model/index.html"
    filterset_class = SensorReadEventFilter
    queryset = SensorReadEvent.objects.all().order_by('-timestamp')


class ControlBoardEventsView(SingleTableMixin, FilterView):
    model = ControlBoardEvent
    table_class = ControlBoardReadingTable
    template_name = "model/control_board.html"
    filterset_class = ControlBoardEventFilter
    queryset = ControlBoardEvent.objects.all().order_by('-timestamp')


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def get_sensors_read_event_in_csv(request):
    sensors_read_events = SensorReadEvent.objects.all().order_by('timestamp')
    rows = [['Placa Controladora', 'ID do Sensor', 'Timestamp', 'Timestamp', 'Valor Lido']]
    for sensor_read in sensors_read_events:
        dt = timezone.localtime(sensor_read.timestamp).strftime('%d/%m/%Y %H:%M:%S')
        rows.append(
            [sensor_read.sensor.control_board.nickname, sensor_read.sensor.sensor_id, dt, sensor_read.value_read])

    return __generate_csv('senso_read_events.csv', rows, request)


def get_peak_delay_in_csv(request):
    start_date_filter = request.GET.get('start') if request.GET.get('start') else None
    end_date_filter = request.GET.get('end') if request.GET.get('end') else None
    results = analyzer.get_peak_delay(start_date_filter=start_date_filter, end_date_filter=end_date_filter)
    rows = [['Modelo', 'Data/Hora Detecçao Superfície', 'Data/Hora Detecção Ralo', 'Diferença']]
    for result in results:
        rows.append([result['prototype_side'], result['surface_rain_timestamp'], result['drain_rain_timestamp'],
                     result['diff']])

    return __generate_csv('atraso_de_pico.csv', rows, request)


def get_pluviometer_reading_in_csv(request):
    start_date_filter = request.GET.get('start') if request.GET.get('start') else None
    end_date_filter = request.GET.get('end') if request.GET.get('end') else None
    results = analyzer.get_pluviometer_reading(start_date_filter=start_date_filter, end_date_filter=end_date_filter)
    rows = [['Sensor', 'Data/Hora', 'Medição']]
    for result in results:
        rows.append([result['sensor_id'], result['timestamp'], result['pluviometer_count']])

    return __generate_csv('pluviometro.csv', rows, request)


def __generate_csv(csv_filname: str, rows, request):
    sep = ';' if request.GET.get('sep') == 'sc' else ','
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer, delimiter=sep, quotechar='"', quoting=csv.QUOTE_ALL)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                     content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="' + csv_filname + '"'
    return response
