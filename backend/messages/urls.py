"""GeoConnect messages: URL configuration (nested under /api/rooms/<id>/)."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.RoomMessagesView.as_view(), name="api-rooms-messages"),
]