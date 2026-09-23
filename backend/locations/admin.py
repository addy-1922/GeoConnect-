from django.contrib import admin

from .models import MapMarker, UserLocation


@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ("user", "latitude", "longitude", "updated_at")
    search_fields = ("user__username",)


@admin.register(MapMarker)
class MapMarkerAdmin(admin.ModelAdmin):
    list_display = ("title", "marker_type", "room", "created_by", "created_at")
    list_filter = ("marker_type",)
    search_fields = ("title", "room__name")