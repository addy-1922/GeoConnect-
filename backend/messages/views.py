"""GeoConnect messages: REST views (history + REST fallback for sending)."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rooms.permissions import IsRoomMember, get_membership
from rooms.views import RoomScopedView

from .models import RoomMessage
from .serializers import RoomMessageSerializer
from .services import create_message


class RoomMessagesView(RoomScopedView):
    """GET message history (newest last) | POST send a message (relayed live)."""

    permission_classes = [IsAuthenticated, IsRoomMember]

    def get(self, request, room_id):
        before = request.query_params.get("before")
        try:
            limit = max(1, min(int(request.query_params.get("limit", 50)), 200))
        except ValueError:
            limit = 50

        qs = (
            RoomMessage.objects.filter(room_id=room_id)
            .select_related("sender", "sender__profile")
            .order_by("-id")
        )
        if before:
            qs = qs.filter(id__lt=before)
        messages = list(qs[:limit])
        messages.reverse()
        return Response(RoomMessageSerializer(messages, many=True).data)

    def post(self, request, room_id):
        serializer = RoomMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if get_membership(request.user, self.room) is None:
            return Response({"detail": "You are not a member."}, status=403)
        message = create_message(
            self.room,
            request.user,
            serializer.validated_data["content"],
        )
        return Response(RoomMessageSerializer(message).data, status=201)