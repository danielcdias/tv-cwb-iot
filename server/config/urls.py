from django.conf.urls import include
from django.contrib import admin
from django.urls import path
from rest_framework import routers

from config.expiring_token import obtain_expiring_auth_token
from model.api.viewsets import BoardVendorViewSet, BoardModelViewSet, ControlBoardViewSet, SensorTypeViewSet, \
    SensorViewSet, SensorReadEventViewSet, NotificationUserViewSet, \
    ControlBoardEventViewSet, message_receiver

router = routers.DefaultRouter()
router.register(r'boardvendors', BoardVendorViewSet, basename="BoardVendor")
router.register(r'boardmodels', BoardModelViewSet, basename="BoardModel")
router.register(r'controlboards', ControlBoardViewSet, basename="ControlBoard")
router.register(r'controlboardevents', ControlBoardEventViewSet, basename="ControlBoardEvent")
router.register(r'sensortypes', SensorTypeViewSet, basename="SensorType")
router.register(r'sensors', SensorViewSet, basename="Sensor")
router.register(r'sensorreadevents', SensorReadEventViewSet, basename="SensorReadEvent")
router.register(r'notificationusers', NotificationUserViewSet, basename="NotificationUser")

urlpatterns = [
    path('', include('model.urls')),
    path('', include(router.urls)),
    path('message_receiver/', message_receiver),
    path('admin/', admin.site.urls),
    path('api-token-auth/', obtain_expiring_auth_token),
]
