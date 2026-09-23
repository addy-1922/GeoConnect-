from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "is_sharing_location", "last_seen")
    list_filter = ("status", "is_sharing_location")
    search_fields = ("user__username", "user__email")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


# Extend the default User admin with the inline Profile.
class UserAdmin(DjangoUserAdmin):
    inlines = (ProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)