from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "message", "room", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("user__username", "message")
    autocomplete_fields = ("user", "actor", "room")