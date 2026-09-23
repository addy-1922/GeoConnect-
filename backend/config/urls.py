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
from django.contrib import admin
from django.urls import include, path, re_path

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
    path("media/<path:path>", api.media_view, name="media"),
]

# SPA catch-all: everything that is not API, WebSocket, media, admin or static
# falls through to the built React app so client-side routes work.
urlpatterns.append(
    re_path(r"^(?!api/|ws/|media/|admin/|static/).*", api.spa_index_view, name="spa-index")
)