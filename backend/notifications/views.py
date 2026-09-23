"""GeoConnect notifications: REST views."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


@api_view(["GET"])
def notification_list_view(request):
    """List the current user's notifications, newest first."""
    unread_only = request.query_params.get("unread") == "true"
    qs = Notification.objects.filter(user=request.user).select_related("actor", "room")
    if unread_only:
        qs = qs.filter(is_read=False)
    qs = qs[:50]
    return Response(NotificationSerializer(qs, many=True).data)


@api_view(["GET"])
def unread_count_view(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({"count": count})


@api_view(["POST"])
def mark_read_view(request, pk):
    notification = Notification.objects.filter(user=request.user, pk=pk).first()
    if notification is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response(NotificationSerializer(notification).data)


@api_view(["POST"])
def mark_all_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"detail": "All notifications marked as read."})