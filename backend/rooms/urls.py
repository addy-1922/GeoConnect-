"""GeoConnect rooms: URL configuration (mounted at /api/rooms/)."""

from django.urls import path

from events import views as event_views
from locations import views as location_views
from messages import views as message_views

from . import views

urlpatterns = [
    path("", views.RoomListCreateView.as_view(), name="api-rooms-list"),
    path("search/", views.search_view, name="api-search"),
    path(
        "<int:room_id>/",
        views.RoomDetailView.as_view(),
        name="api-rooms-detail",
    ),
    path(
        "<int:room_id>/join/",
        views.RoomJoinView.as_view(),
        name="api-rooms-join",
    ),
    path(
        "<int:room_id>/leave/",
        views.RoomLeaveView.as_view(),
        name="api-rooms-leave",
    ),
    path(
        "<int:room_id>/members/",
        views.RoomMembersView.as_view(),
        name="api-rooms-members",
    ),
    path(
        "<int:room_id>/members/<int:user_id>/",
        views.RoomMemberDetailView.as_view(),
        name="api-rooms-member-detail",
    ),
    path(
        "<int:room_id>/messages/",
        message_views.RoomMessagesView.as_view(),
        name="api-rooms-messages",
    ),
    path(
        "<int:room_id>/locations/",
        location_views.room_locations_view,
        name="api-rooms-locations",
    ),
    path(
        "<int:room_id>/nearby/",
        location_views.room_nearby_view,
        name="api-rooms-nearby",
    ),
    path(
        "<int:room_id>/events/",
        event_views.RoomEventsView.as_view(),
        name="api-rooms-events",
    ),
    path(
        "<int:room_id>/events/<int:pk>/",
        event_views.RoomEventDetailView.as_view(),
        name="api-rooms-event-detail",
    ),
    path(
        "<int:room_id>/markers/",
        location_views.RoomMarkersView.as_view(),
        name="api-rooms-markers",
    ),
    path(
        "<int:room_id>/markers/<int:pk>/",
        location_views.RoomMarkerDetailView.as_view(),
        name="api-rooms-marker-detail",
    ),
]