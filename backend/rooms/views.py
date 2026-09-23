"""GeoConnect rooms: REST views."""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Room
from .permissions import IsRoomAdminOrOwner, IsRoomMember, IsRoomOwner, get_membership
from . import services
from .serializers import (
    AddMemberSerializer,
    RoomCreateSerializer,
    RoomDetailSerializer,
    RoomListSerializer,
    RoomMemberSerializer,
    RoomUpdateSerializer,
    RoleUpdateSerializer,
)

User = get_user_model()


class RoomScopedView(APIView):
    """Loads self.room and rejects non-members with 404 (no info leak)."""

    permission_classes = [IsAuthenticated, IsRoomMember]

    def initial(self, request, *args, **kwargs):
        room_pk = self.kwargs.get("room_id")
        self.room = get_object_or_404(Room, pk=room_pk)
        if get_membership(request.user, self.room) is None:
            from django.http import Http404

            raise Http404("Room not found.")
        super().initial(request, *args, **kwargs)


class RoomListCreateView(APIView):
    """GET my rooms | POST create a room (creator becomes OWNER)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = (
            Room.objects.annotate(num_members=Count("memberships"))
            .filter(memberships__user=request.user)
            .distinct()
        )
        serializer = RoomListSerializer(
            rooms,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def post(self, request):
        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = services.create_room(
            request.user,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            is_private=serializer.validated_data.get("is_private", False),
        )
        return Response(
            RoomDetailSerializer(
                room,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class RoomDetailView(RoomScopedView):
    """GET room detail | PATCH name/description/private (ADMIN+) | DELETE (OWNER)."""

    def get(self, request, room_id):
        serializer = RoomDetailSerializer(
            self.room,
            context={"request": request},
        )
        return Response(serializer.data)

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAuthenticated(), IsRoomAdminOrOwner()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsRoomOwner()]
        return super().get_permissions()

    def patch(self, request, room_id):
        serializer = RoomUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        room = services.update_room(request.user, self.room, **serializer.validated_data)
        return Response(
            RoomDetailSerializer(room, context={"request": request}).data
        )

    def delete(self, request, room_id):
        services.delete_room(request.user, self.room)
        return Response({"detail": "Room deleted."}, status=status.HTTP_204_NO_CONTENT)


class RoomJoinView(APIView):
    """POST to join a public room. Deliberately NOT member-scoped:
    a non-member must be able to reach this endpoint. Private rooms are
    rejected inside rooms.services.join_room (invitation required).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(Room, pk=room_id)
        try:
            services.join_room(request.user, room)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            RoomDetailSerializer(room, context={"request": request}).data
        )


class RoomLeaveView(RoomScopedView):
    """POST to leave a room (OWNER must delete instead)."""

    def post(self, request, room_id):
        try:
            services.leave_room(request.user, self.room)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response({"detail": "You left the room."})


class RoomMembersView(RoomScopedView):
    """GET member list | POST add a member by username (ADMIN+)."""

    def get(self, request, room_id):
        memberships = self.room.memberships.select_related("user", "user__profile").all()
        return Response(RoomMemberSerializer(memberships, many=True).data)

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsRoomAdminOrOwner()]
        return super().get_permissions()

    def post(self, request, room_id):
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        page_user = User.objects.filter(username__iexact=serializer.validated_data["username"]).first()
        if page_user is None:
            return Response(
                {"detail": "No user found with that username."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            membership = services.add_member(
                request.user,
                self.room,
                page_user,
                role=serializer.validated_data.get("role", "MEMBER"),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            RoomMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class RoomMemberDetailView(RoomScopedView):
    """PATCH role | DELETE remove member (ADMIN+; subjects under their level)."""

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT", "DELETE"):
            return [IsAuthenticated(), IsRoomAdminOrOwner()]
        return super().get_permissions()

    def patch(self, request, room_id, user_id):
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = get_object_or_404(User, pk=user_id)
        try:
            membership = services.update_member_role(
                request.user, self.room, target, serializer.validated_data["role"]
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(RoomMemberSerializer(membership).data)

    def delete(self, request, room_id, user_id):
        target = get_object_or_404(User, pk=user_id)
        try:
            services.remove_member(request.user, self.room, target)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response({"detail": "Member removed."}, status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_view(request):
    """Global search: users, rooms (of the user), events and markers (of their rooms)."""
    query = (request.query_params.get("q") or "").strip()
    result = {
        "users": [],
        "rooms": [],
        "events": [],
        "markers": [],
    }
    if not query:
        return Response(result)

    from accounts.serializers import PublicUserSerializer
    from events.models import LocationEvent
    from locations.models import MapMarker
    from .serializers import RoomListSerializer

    result["users"] = PublicUserSerializer(
        User.objects.filter(username__icontains=query)[:10], many=True
    ).data

    my_room_ids = Room.objects.filter(memberships__user=request.user).values_list("id", flat=True)
    result["rooms"] = RoomListSerializer(
        Room.objects.filter(id__in=my_room_ids, name__icontains=query)
        .annotate(num_members=Count("memberships")),
        many=True,
        context={"request": request},
    ).data

    from events.serializers import LocationEventSerializer
    from locations.serializers import MapMarkerSerializer

    result["events"] = LocationEventSerializer(
        LocationEvent.objects.filter(room_id__in=my_room_ids, title__icontains=query)[:10],
        many=True,
        context={"request": request},
    ).data
    result["markers"] = MapMarkerSerializer(
        MapMarker.objects.filter(room_id__in=my_room_ids, title__icontains=query)[:10],
        many=True,
        context={"request": request},
    ).data
    return Response(result)