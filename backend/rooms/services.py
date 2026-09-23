"""GeoConnect rooms: business logic (create / join / leave / manage members).

All state changes and the notifications/real-time broadcasts they trigger live
here so views stay thin and behaviour is easy to unit-test.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from notifications import services as notification_services
from notifications.models import Notification

from .models import Room, RoomMember
from .permissions import get_membership

User = get_user_model()

ROLE_PRIORITY = {
    RoomMember.Role.OWNER: 3,
    RoomMember.Role.ADMIN: 2,
    RoomMember.Role.MEMBER: 1,
}


def _notify_others_in_room(room, actor, message, type_):
    """Create a notification for every room member except the actor."""
    for membership in room.memberships.select_related("user").all():
        if membership.user == actor:
            continue
        notification_services.create_notification(
            membership.user,
            message,
            type_,
            actor=actor,
            room=room,
        )


def create_room(creator, name, description="", is_private=False):
    room = Room.objects.create(
        name=name.strip(),
        description=description.strip(),
        is_private=is_private,
        created_by=creator,
    )
    RoomMember.objects.create(room=room, user=creator, role=RoomMember.Role.OWNER)
    return room


def join_room(user, room, actor=None):
    """Add a user as a MEMBER. Private rooms require a prior invitation."""
    actor = actor or user
    existing = get_membership(user, room)
    if existing:
        return existing
    if room.is_private:
        raise PermissionDenied("This is a private room. You need an invitation to join.")
    membership = RoomMember.objects.create(room=room, user=user, role=RoomMember.Role.MEMBER)
    _notify_others_in_room(
        room,
        user,
        f"{user.username} joined {room.name}",
        Notification.Type.USER_JOINED,
    )
    return membership


def leave_room(user, room):
    """Remove a user from a room. The OWNER must delete the room instead."""
    membership = get_membership(user, room)
    if membership is None:
        return None
    if membership.role == RoomMember.Role.OWNER:
        raise PermissionDenied("The room owner cannot leave. Delete the room instead.")
    if room.memberships.count() == 1:
        raise PermissionDenied("You are the only member; delete the room instead.")
    membership.delete()
    _notify_others_in_room(
        room,
        user,
        f"{user.username} left {room.name}",
        Notification.Type.USER_LEFT,
    )
    return membership


def add_member(actor, room, target_user, role=RoomMember.Role.MEMBER):
    """An OWNER/ADMIN invites a user into the room."""
    existing = get_membership(target_user, room)
    if existing:
        return existing
    membership = RoomMember.objects.create(room=room, user=target_user, role=role)
    notification_services.create_notification(
        target_user,
        f"{actor.username} added you to the room '{room.name}'",
        Notification.Type.MEMBER_ADDED,
        actor=actor,
        room=room,
    )
    return membership


def update_member_role(actor, room, target_user, new_role):
    """Change a member's role, respecting role hierarchy."""
    target = get_membership(target_user, room)
    if target is None:
        raise PermissionDenied("That user is not a member of this room.")
    if target.role == RoomMember.Role.OWNER:
        raise PermissionDenied("The owner's role cannot be changed.")
    if new_role == RoomMember.Role.OWNER:
        raise PermissionDenied("Roles can only be OWNER, ADMIN or MEMBER.")

    actor_membership = get_membership(actor, room)
    if actor_membership is None:
        raise PermissionDenied("You are not a member of this room.")
    if ROLE_PRIORITY[actor_membership.role] <= ROLE_PRIORITY[target.role]:
        raise PermissionDenied("You cannot change the role of a member at your level or above.")

    target.role = new_role
    target.save(update_fields=["role", "joined_at"])
    notification_services.notify_role_changed(target_user, room, new_role)
    return target


def remove_member(actor, room, target_user, grace_tokens=None):
    """Remove a member; the OWNER and the actor themselves can never be removed by admins."""
    target = get_membership(target_user, room)
    if target is None:
        return None
    if target.role == RoomMember.Role.OWNER:
        raise PermissionDenied("The room owner cannot be removed.")
    actor_membership = get_membership(actor, room)
    if actor_membership is None:
        raise PermissionDenied("You are not a member of this room.")
    if ROLE_PRIORITY[actor_membership.role] <= ROLE_PRIORITY[target.role]:
        raise PermissionDenied("You cannot remove a member at your level or above.")
    target.delete()
    _notify_others_in_room(
        room,
        actor,
        f"{target_user.username} was removed from {room.name}",
        Notification.Type.USER_LEFT,
    )
    return target


def update_room(actor, room, **fields):
    for key in ("name", "description", "is_private"):
        if key in fields and fields[key] is not None:
            setattr(room, key, fields[key])
    room.updated_at = timezone.now()
    room.save(update_fields=["name", "description", "is_private", "updated_at"])
    _notify_others_in_room(
        room,
        actor,
        f"Room '{room.name}' was updated",
        Notification.Type.SYSTEM,
    )
    return room


def delete_room(actor, room):
    """Delete a room (OWNER only). Notify members first; notifications persist."""
    members = list(room.memberships.select_related("user").all())
    name = room.name
    for membership in members:
        if membership.user == actor:
            continue
        notification_services.create_notification(
            membership.user,
            f"Room '{name}' was deleted",
            Notification.Type.ROOM_DELETED,
            actor=actor,
        )
    room.delete()
    return name


def build_room_snapshot(user, room_id):
    """Everything a client needs right after joining the room WebSocket.

    Kept DB-lean: only last-known locations of *authorized, sharing* members
    are included - never a stream of historical coordinates.
    """
    from events.models import LocationEvent
    from events.serializers import LocationEventSerializer
    from locations.models import MapMarker, UserLocation
    from locations.presence import online_user_ids
    from locations.serializers import MapMarkerSerializer
    from messages.models import RoomMessage
    from messages.serializers import RoomMessageSerializer

    room = Room.objects.get(pk=room_id)
    membership = get_membership(user, room)
    role = membership.role if membership else None

    memberships = room.memberships.select_related("user", "user__profile").all()
    participants = []
    for m in memberships:
        from accounts.serializers import PublicUserSerializer

        participant = PublicUserSerializer(m.user).data
        participant["role"] = m.role
        participants.append(participant)

    messages = list(
        RoomMessage.objects.filter(room_id=room_id).select_related("sender").order_by("-id")[:50]
    )
    messages.reverse()

    locations = {}
    for location in (
        UserLocation.objects.select_related("user", "user__profile")
        .filter(
            user__room_memberships__room_id=room_id,
            user__profile__is_sharing_location=True,
        )
        .distinct()
    ):
        locations[str(location.user_id)] = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy": location.accuracy,
            "updated_at": location.updated_at.isoformat(),
        }

    return {
        "type": "room_snapshot",
        "room": {"id": room.id, "name": room.name, "is_private": room.is_private},
        "my_role": role,
        "participants": participants,
        "online_ids": sorted(online_user_ids(room_id)),
        "messages": RoomMessageSerializer(messages, many=True).data,
        "locations": locations,
        "events": LocationEventSerializer(
            LocationEvent.objects.filter(room_id=room_id), many=True
        ).data,
        "markers": MapMarkerSerializer(MapMarker.objects.filter(room_id=room_id), many=True).data,
    }