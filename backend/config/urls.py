"""
GeoConnect root URL configuration.

API namespaces (mounted under /api/):
    /api/auth/          register, login, logout, csrf
    /api/users/         me / profile updates, user search
    /api/rooms/         rooms, members, join/leave, messages, locations, events,
                        markers, nearby
    /api/notifications/ real-time notification inbox
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts import views as accounts_views
from config import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", api.health_view, name="api-health"),
    path("api/auth/", include("accounts.urls")),
    path("api/users/me/", accounts_views.me_view, name="api-users-me"),
    path("api/users/", accounts_views.user_list_view, name="api-users-list"),
    path("api/rooms/", include("rooms.urls")),
    path("api/notifications/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)