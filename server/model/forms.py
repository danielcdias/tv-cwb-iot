from django import forms
from django.conf import settings


class DataAvailable(forms.Form):
    DATA_TEMPERATURE = 0
    DATA_PLUVIOMETER = 1
    DATA_PEAK_DELAY = 2
    DATA_WATER_ABSORPTION = 3

    DataOptions = (
        (DATA_TEMPERATURE, "Temperatura"),
        (DATA_PLUVIOMETER, "Precipitação"),
        (DATA_PEAK_DELAY, "Atraso de Pico"),
        (DATA_WATER_ABSORPTION, "Absorção de água"),
    )

    data_type = forms.ChoiceField(choices=DataOptions, required=True, label="Comparação")
    start_timestamp = forms.DateTimeField(input_formats=(settings.DATETIME_FORMAT,), required=False,
                                          label="Data/Hora Inicial")
    end_timestamp = forms.DateTimeField(input_formats=(settings.DATETIME_FORMAT,), required=False,
                                        label="Data/Hora Final")
