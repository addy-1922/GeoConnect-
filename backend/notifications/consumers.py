"""GeoConnect notifications: WebSocket consumer for the current user's inbox."""

from asgiref.sync import sync_to_async

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Connects to /ws/notifications/ and receives that user's notifications."""

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.user_id = user.id
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._mark_seen()

    async def disconnect(self, code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Notifications are server-push only; ignore client frames.
        await self.send_json({"type": "ack"})

    async def notification(self, event):
        """Sent to this group by notifications.services.create_notification."""
        await self.send_json(event)

    @sync_to_async
    def _mark_seen(self):
        from accounts.services import mark_seen

        mark_seen(self.scope.get("user"))