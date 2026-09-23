"""
ASGI config for GeoConnect (config project).

ProtocolTypeRouter dispatches by protocol:
  - "http"      -> standard Django ASGI application (endpoints + admin)
  - "websocket" -> Channels URLRouter wrapped in AuthMiddlewareStack, so the
                   normal Django session cookie authenticates socket users.

WebSocket routes are defined in config/routing.py.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django so its application registry is populated before we
# reference any Channels consumers below.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from config import routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns)),
    }
)