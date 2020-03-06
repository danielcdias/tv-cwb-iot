import django_filters

from .models import SensorReadEvent, ControlBoard, ControlBoardEvent, Sensor


def get_sensor_ids():
    sensors = Sensor.objects.all().filter(active=True).order_by('sensor_id')
    aux = []
    for s in sensors:
        if s.sensor_id not in aux:
            aux.append(s.sensor_id)
    return [(t, t) for t in aux]


class SensorReadEventFilter(django_filters.FilterSet):
    sensor__sensor_id = django_filters.MultipleChoiceFilter(choices=get_sensor_ids())
    timestamp = django_filters.DateTimeFromToRangeFilter(label="Data/hora")
    value_read = django_filters.NumberFilter(label="Valor lido", lookup_expr='contains')
    sensor__control_board__prototype_side = django_filters.ChoiceFilter(choices=ControlBoard.PrototypeSide)

    class Meta:
        model = SensorReadEvent
        fields = ('sensor__sensor_id', 'timestamp', 'value_read', 'sensor__control_board__prototype_side')


class ControlBoardEventFilter(django_filters.FilterSet):
    control_board__nickname = django_filters.CharFilter(label="Apelido", lookup_expr='contains')
    control_board__prototype_side = django_filters.ChoiceFilter(choices=ControlBoard.PrototypeSide)
    timestamp = django_filters.DateTimeFromToRangeFilter(label="Data/hora")
    status_received = django_filters.CharFilter(label="Valor lido", lookup_expr='contains')

    class Meta:
        model = ControlBoardEvent
        fields = ('control_board__nickname', 'control_board__prototype_side', 'timestamp', 'status_received')
