from django.urls import path
from model import views

app_name = 'model'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('boards/', views.ControlBoardEventsView.as_view(), name='boards'),
    path('csv/sensorreadevents/', views.get_sensors_read_event_in_csv, name='csv_sensorreadevents'),
    path('csv/peakdelay/', views.get_peak_delay_in_csv, name='csv_peakdelay'),
    path('csv/pluviometer/', views.get_pluviometer_reading_in_csv, name='csv_pluviometer'),
]
