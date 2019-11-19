from django.contrib.auth.models import User
from rest_framework.serializers import ModelSerializer, CharField

from model.models import BoardVendor, BoardModel, ControlBoard, SensorType, Sensor, SensorReadEvent, NotificationUser, \
    ControlBoardEvent


class BoardVendorSerializer(ModelSerializer):
    class Meta:
        model = BoardVendor
        fields = ('id', 'description',)


class BoardModelSerializer(ModelSerializer):
    board_vendor = BoardVendorSerializer()

    class Meta:
        model = BoardModel
        fields = ('id', 'description', 'board_vendor',)


class ControlBoardSerializer(ModelSerializer):
    board_model = BoardModelSerializer()

    class Meta:
        model = ControlBoard
        fields = ('id', 'nickname', 'mac_address', 'short_mac_id', 'prototype_side_description', 'board_model',)


class ControlBoardEventSerializer(ModelSerializer):
    nickname = CharField(source='control_board.nickname', read_only=True)
    short_mac_id = CharField(source='control_board.short_mac_id', read_only=True)
    prototype_side_description = CharField(source='control_board.prototype_side_description', read_only=True)

    class Meta:
        model = ControlBoardEvent
        fields = ('id', 'short_mac_id', 'nickname', 'prototype_side_description', 'timestamp', 'status_received',)


class SensorTypeSerializer(ModelSerializer):
    class Meta:
        model = SensorType
        fields = ('id', 'sensor_type', 'description', 'data_sheet', 'precision',)


class SensorSerializer(ModelSerializer):
    sensor_type = SensorTypeSerializer()
    control_board = ControlBoardSerializer()

    class Meta:
        model = Sensor
        fields = ('id', 'sensor_id', 'description', 'sensor_type', 'sensor_role_description', 'control_board',)


class SensorReadEventSerializer(ModelSerializer):
    sensor_id = CharField(source='sensor.sensor_id', read_only=True)
    prototype_side_description = CharField(source='sensor.control_board.prototype_side_description', read_only=True)

    class Meta:
        model = SensorReadEvent
        fields = ('id', 'prototype_side_description', 'sensor_id', 'timestamp', 'value_read',)


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email',)


class NotificationUserSerializer(ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = NotificationUser
        fields = ('id', 'notify_errors', 'user',)
