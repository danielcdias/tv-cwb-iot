from django.contrib import admin

from .models import BoardVendor, BoardModel, ControlBoard, SensorType, Sensor, NotificationUser


class BoardVendorAdmin(admin.ModelAdmin):
    model = BoardVendor
    extra = 0
    ordering = ('description',)


class BoardModelAdmin(admin.ModelAdmin):
    model = BoardModel
    extra = 0
    ordering = ('description',)


class ControlBoardAdmin(admin.ModelAdmin):
    model = ControlBoard
    extra = 0
    ordering = ('nickname',)


class SensorTypeAdmin(admin.ModelAdmin):
    model = SensorType
    extra = 0
    ordering = ('sensor_type',)


class SensorAdmin(admin.ModelAdmin):
    model = Sensor
    extra = 0
    ordering = ('sensor_id',)


class NotificationUserAdmin(admin.ModelAdmin):
    model = NotificationUser
    extra = 0
    ordering = ('user__username',)


admin.site.register(BoardVendor, BoardVendorAdmin)
admin.site.register(BoardModel, BoardModelAdmin)
admin.site.register(ControlBoard, ControlBoardAdmin)
admin.site.register(SensorType, SensorTypeAdmin)
admin.site.register(Sensor, SensorAdmin)
admin.site.register(NotificationUser, NotificationUserAdmin)
