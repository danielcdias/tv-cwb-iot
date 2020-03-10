from django.urls import path
from model import views

app_name = 'model'
urlpatterns = [
    path('', views.form_data_available, name='index'),
    path('sensors/', views.SensorsView.as_view(), name='sensors'),
    path('boards/', views.ControlBoardEventsView.as_view(), name='boards'),
    path('csv/sensor_read_events/', views.get_sensors_read_event_in_csv, name='csv_sensorreadevents'),
    path('csv/peak_delay/', views.get_peak_delay_in_csv, name='csv_peakdelay'),
    path('csv/pluviometer/', views.get_pluviometer_rain_events_in_csv, name='csv_pluviometer'),
    path('csv/water_absorption/', views.get_absorption_readings_in_csv, name='csv_waterabsorption'),
    path('csv/temperature/', views.get_temperature_readings_in_csv, name='csv_temperature'),
]
