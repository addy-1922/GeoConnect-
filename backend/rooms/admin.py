from django.contrib import admin

from .models import Room, RoomMember


class RoomMemberInline(admin.TabularInline):
    model = RoomMember
    extra = 0


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "is_private", "created_by", "created_at")
    list_filter = ("is_private",)
    search_fields = ("name", "description")
    inlines = (RoomMemberInline,)


@admin.register(RoomMember)
class RoomMemberAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("room__name", "user__username")