"""GeoConnect locations: REST views (room-scoped, member-authorized)."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import PublicUserSerializer
from rooms.models import Room, RoomMember
from rooms.permissions import IsRoomMember, get_membership
from rooms.views import RoomScopedView

from . import services
from .geo import format_distance, haversine_meters
from .models import MapMarker, UserLocation
from .serializers import MapMarkerSerializer


def _member_or_404(user, room):
    membership = get_membership(user, room)
    if membership is None:
        from django.http import Http404

        raise Http404("Room not found.")
    return membership


def _authorized_sharing_members(room):
    """Last-known locations of members who have sharing enabled."""
    locations = (
        UserLocation.objects.select_related("user", "user__profile")
        .filter(
            user__room_memberships__room_id=room.id,
            user__profile__is_sharing_location=True,
        )
        .distinct()
    )
    rows = []
    for location in locations:
        rows.append(
            {
                "user": PublicUserSerializer(location.user).data,
                **location.to_dict(),
            }
        )
    return rows


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def room_locations_view(request, room_id):
    """List authorized participants' last-known locations (sharing only)."""
    room = get_object_or_404(Room, pk=room_id)
    _member_or_404(request.user, room)
    return Response(_authorized_sharing_members(room))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def room_nearby_view(request, room_id):
    """Distances from the current user to other sharing members in the room.

    The caller must themselves be sharing their location (that is their
    reference point); otherwise there is nothing to measure distance from.
    """
    room = get_object_or_404(Room, pk=room_id)
    _member_or_404(request.user, room)

    mine = UserLocation.objects.filter(user=request.user).first()
    if mine is None or not request.user.profile.is_sharing_location:
        return Response(
            {
                "detail": "Enable location sharing to see people nearby.",
                "code": "needs_location",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    nearby = []
    for row in _authorized_sharing_members(room):
        if row["user"]["user_id"] == request.user.id:
            continue
        meters = haversine_meters(mine.latitude, mine.longitude, row["latitude"], row["longitude"])
        nearby.append(
            {
                "user": row["user"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "distance_m": round(meters, 1),
                "distance": format_distance(meters),
            }
        )
    nearby.sort(key=lambda item: item["distance_m"])
    return Response({"reference": {"latitude": mine.latitude, "longitude": mine.longitude}, "nearby": nearby})


class RoomMarkersView(RoomScopedView):
    """GET markers in a room | POST create a marker (member, broadcast live)."""

    permission_classes = [IsAuthenticated, IsRoomMember]

    def get(self, request, room_id):
        markers = MapMarker.objects.filter(room_id=room_id).select_related("created_by")
        return Response(MapMarkerSerializer(markers, many=True).data)

    def post(self, request, room_id):
        serializer = MapMarkerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        marker = services.create_marker(
            self.room,
            request.user,
            title=serializer.validated_data["title"],
            marker_type=serializer.validated_data["marker_type"],
            latitude=serializer.validated_data["latitude"],
            longitude=serializer.validated_data["longitude"],
        )
        return Response(MapMarkerSerializer(marker).data, status=status.HTTP_201_CREATED)


class RoomMarkerDetailView(RoomScopedView):
    """GET/PATCH/DELETE a single marker.

    ADMIN/OWNER may manage any marker; otherwise the creator manages their own.
    All checks are enforced on the backend regardless of UI state.
    """

    permission_classes = [IsAuthenticated, IsRoomMember]

    def get_object(self):
        return get_object_or_404(
            MapMarker,
            pk=self.kwargs["pk"],
            room_id=self.kwargs["room_id"],
        )

    def _can_manage(self, marker):
        role = get_membership(self.request.user, self.room).role
        if role in (RoomMember.Role.OWNER, RoomMember.Role.ADMIN):
            return True
        return marker.created_by_id == self.request.user.id

    def get(self, request, room_id, pk):
        return Response(MapMarkerSerializer(self.get_object()).data)

    def patch(self, request, room_id, pk):
        marker = self.get_object()
        if not self._can_manage(marker):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = MapMarkerSerializer(marker, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        marker = serializer.save()
        return Response(MapMarkerSerializer(marker).data)

    def delete(self, request, room_id, pk):
        marker = self.get_object()
        if not self._can_manage(marker):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        marker.delete()
        return Response({"detail": "Marker deleted."}, status=status.HTTP_204_NO_CONTENT)