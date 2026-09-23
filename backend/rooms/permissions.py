"""GeoConnect rooms: DRF permissions enforced at the object level."""

from rest_framework.permissions import BasePermission

from .models import RoomMember


def get_membership(user, room):
    """Return the user's RoomMember row for a room, or None."""
    if user is None or not user.is_authenticated:
        return None
    return RoomMember.objects.filter(room=room, user=user).first()


def membership_role(user, room):
    membership = get_membership(user, room)
    return membership.role if membership else None


class IsRoomMember(BasePermission):
    """Authenticated user must be a member of `view.room`."""

    def has_permission(self, request, view):
        room = getattr(view, "room", None)
        if room is None:
            return False
        return get_membership(request.user, room) is not None


class IsRoomAdminOrOwner(IsRoomMember):
    """Member must hold the ADMIN or OWNER role in the room."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        role = membership_role(request.user, view.room)
        return role in (RoomMember.Role.ADMIN, RoomMember.Role.OWNER)


class IsRoomOwner(BasePermission):
    def has_permission(self, request, view):
        room = getattr(view, "room", None)
        if room is None:
            return False
        role = membership_role(request.user, room)
        return role == RoomMember.Role.OWNER