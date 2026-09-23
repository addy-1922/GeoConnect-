from django.contrib import admin

from .models import LocationEvent


@admin.register(LocationEvent)
class LocationEventAdmin(admin.ModelAdmin):
    list_display = ("title", "room", "created_by", "start_time", "created_at")
    search_fields = ("title", "description", "room__name")