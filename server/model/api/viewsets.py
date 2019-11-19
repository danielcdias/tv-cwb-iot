import logging

from django.utils import timezone
from config import settings
from pytz import timezone as tz
from datetime import datetime

from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ReadOnlyModelViewSet

from config.expiring_token import ExpiringTokenAuthentication
from model.api.serializers import BoardVendorSerializer, BoardModelSerializer, ControlBoardSerializer, \
    SensorTypeSerializer, SensorSerializer, SensorReadEventSerializer, NotificationUserSerializer, \
    ControlBoardEventSerializer
from model.models import BoardVendor, BoardModel, ControlBoard, SensorType, Sensor, SensorReadEvent, NotificationUser, \
    ControlBoardEvent
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status

CMD_SERVER_TIMESTAMP = "T"


class BoardVendorViewSet(ReadOnlyModelViewSet):
    queryset = BoardVendor.objects.all()
    serializer_class = BoardVendorSerializer
    filter_backends = (SearchFilter,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class BoardModelViewSet(ReadOnlyModelViewSet):
    queryset = BoardModel.objects.all()
    serializer_class = BoardModelSerializer
    filter_backends = (SearchFilter,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class ControlBoardViewSet(ReadOnlyModelViewSet):
    queryset = ControlBoard.objects.all()
    serializer_class = ControlBoardSerializer
    filter_backends = (SearchFilter,)
    search_fields = 'nickname'
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class ControlBoardEventViewSet(ReadOnlyModelViewSet):
    queryset = ControlBoardEvent.objects.all()
    serializer_class = ControlBoardEventSerializer
    filter_backends = (SearchFilter,)
    search_fields = ('control_board__nickname', 'timestamp', 'status_received')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class SensorTypeViewSet(ReadOnlyModelViewSet):
    queryset = SensorType.objects.all()
    serializer_class = SensorTypeSerializer
    filter_backends = (SearchFilter,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class SensorViewSet(ReadOnlyModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    filter_backends = (SearchFilter,)
    search_fields = ('control_board__nickname', 'sensor_id')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class SensorReadEventViewSet(ReadOnlyModelViewSet):
    queryset = SensorReadEvent.objects.all()
    serializer_class = SensorReadEventSerializer
    filter_backends = (SearchFilter,)
    search_fields = ('sensor__sensor_id', 'timestamp')
    permission_classes = (IsAuthenticatedOrReadOnly,)
    authentication_classes = (ExpiringTokenAuthentication,)


class NotificationUserViewSet(ReadOnlyModelViewSet):
    queryset = NotificationUser.objects.all()
    serializer_class = NotificationUserSerializer
    filter_backends = (SearchFilter,)
    permission_classes = (IsAuthenticated,)
    authentication_classes = (ExpiringTokenAuthentication,)


@api_view(['POST'])
@authentication_classes([ExpiringTokenAuthentication])
@permission_classes([IsAuthenticated])
def message_receiver(request):
    logger = logging.getLogger("tvcwb")
    logger.debug("'message_receiver' called. Request data: {}".format(request.data))
    result = Response("Object created with succes!", status.HTTP_201_CREATED)
    data = request.data
    if data and ("topic" in data) and ("message" in data):
        topic = request.data['topic']
        payload = request.data['message']

        mac_end = (topic[-8:-6] + ":" + topic[-6:-4]
                   if len(topic) > 24 else topic[-4:-2] + ":" + topic[-2:])
        sensor_id = (topic[-3:] if len(topic) > 24 else None)
        query = ControlBoard.objects.filter(mac_address__endswith=mac_end)
        if query:
            board = query[0]
            value_str = payload
            timestamp = timezone.now()
            if (len(payload) >= 12) and (payload.find(CMD_SERVER_TIMESTAMP) > -1):
                value_str = payload[0:payload.find(CMD_SERVER_TIMESTAMP)]
                timestamp = timezone.localtime(
                    datetime.fromtimestamp(int(payload[payload.find(CMD_SERVER_TIMESTAMP) + 1:]),
                                           tz=tz(settings.TIME_ZONE)))
            if sensor_id:
                subquery = board.sensor_set.all().filter(sensor_id=sensor_id)
                if subquery:
                    sensor = subquery[0]
                    try:
                        value = float(value_str)
                        if sensor.sensor_type.precision > 0:
                            value = value / (10 ** sensor.sensor_type.precision)
                        sensor_read_event = sensor.sensorreadevent_set.create(timestamp=timestamp, value_read=value)
                        sensor_read_event.save()
                    except ValueError:
                        logger.warning("Value received is not a valid float: {}".format(value_str))
                        result = Response("Value received is not a valid float: {}".format(value_str),
                                          status.HTTP_400_BAD_REQUEST)
                else:
                    logger.warning(
                        "No sensor was found with ID {} for the control board {}.".format(sensor_id,
                                                                                          board.nickname))
                    result = Response("No sensor was found with ID {} for the control board {}.".format(sensor_id,
                                                                                                        board.nickname),
                                      status.HTTP_400_BAD_REQUEST)
            else:
                board_event_received = board.controlboardevent_set.create(timestamp=timestamp,
                                                                          status_received=value_str[:20])
                board_event_received.save()
        else:
            logger.warning("No control board was found with mac address ending with {}.".format(mac_end))
            result = Response("No control board was found with mac address ending with {}.".format(mac_end),
                              status.HTTP_400_BAD_REQUEST)
    else:
        logger.warning("The data informed is invalid.")
        result = Response("The data informed is invalid.", status.HTTP_400_BAD_REQUEST)
    return result
