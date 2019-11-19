import django_filters

from .models import SensorReadEvent, ControlBoard


class SensorReadEventFilter(django_filters.FilterSet):
    sensor__sensor_id = django_filters.CharFilter(label="ID do sensor", lookup_expr='contains')
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
    status_received = django_filters.CharFilter(label="Valor lido")

    class Meta:
        model = SensorReadEvent
        fields = ('control_board__nickname', 'control_board__prototype_side', 'timestamp', 'status_received')
