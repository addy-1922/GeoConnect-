from django.contrib import admin

from .models import RoomMessage


@admin.register(RoomMessage)
class RoomMessageAdmin(admin.ModelAdmin):
    list_display = ("room", "sender", "short_content", "created_at")
    search_fields = ("content", "sender__username", "room__name")

    @admin.display(description="Message")
    def short_content(self, obj):
        return obj.content[:60]