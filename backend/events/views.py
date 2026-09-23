"""GeoConnect events: REST views (room-scoped, member-authorized)."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rooms.models import RoomMember
from rooms.permissions import IsRoomMember, get_membership
from rooms.views import RoomScopedView

from . import services
from .models import LocationEvent
from .serializers import LocationEventSerializer


class RoomEventsView(RoomScopedView):
    """GET events in a room | POST create an event (member, broadcast live)."""

    permission_classes = [IsAuthenticated, IsRoomMember]

    def get(self, request, room_id):
        events = LocationEvent.objects.filter(room_id=room_id).select_related("created_by")
        return Response(LocationEventSerializer(events, many=True).data)

    def post(self, request, room_id):
        serializer = LocationEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = services.create_event(
            self.room,
            request.user,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            latitude=serializer.validated_data["latitude"],
            longitude=serializer.validated_data["longitude"],
            start_time=serializer.validated_data.get("start_time"),
        )
        return Response(
            LocationEventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )


class RoomEventDetailView(RoomScopedView):
    """GET/PATCH/DELETE a single event.

    ADMIN/OWNER manage any event; otherwise the creator manages their own.
    """

    permission_classes = [IsAuthenticated, IsRoomMember]

    def get_object(self):
        return get_object_or_404(
            LocationEvent,
            pk=self.kwargs["pk"],
            room_id=self.kwargs["room_id"],
        )

    def _can_manage(self, event):
        role = get_membership(self.request.user, self.room).role
        if role in (RoomMember.Role.OWNER, RoomMember.Role.ADMIN):
            return True
        return event.created_by_id == self.request.user.id

    def get(self, request, room_id, pk):
        return Response(LocationEventSerializer(self.get_object()).data)

    def patch(self, request, room_id, pk):
        event = self.get_object()
        if not self._can_manage(event):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = LocationEventSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(LocationEventSerializer(event).data)

    def delete(self, request, room_id, pk):
        event = self.get_object()
        if not self._can_manage(event):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        event.delete()
        return Response({"detail": "Event deleted."}, status=status.HTTP_204_NO_CONTENT)