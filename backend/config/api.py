"""
Health-check endpoints.

Used by the React frontend (and by `npm run dev` phase 1 verification) to
confirm that the API server is reachable and that PostgreSQL + Redis answer.
"""

from datetime import datetime, timezone

import redis
from django.conf import settings
from django.db import connection
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve as django_serve


def spa_index_view(request):
    """Serves the built React app's index.html for client-side routes.

    WhiteNoise already handles /assets/* from the build; this catch-all is the
    SPA fallback so URLs like /rooms/12 render the app instead of 404ing.
    """
    index_path = settings.FRONTEND_BUILD_DIR / "index.html"
    if not index_path.exists():
        raise Http404("Frontend not built.")
    return HttpResponse(index_path.read_text(), content_type="text/html")


def media_view(request, path):
    """Serves uploaded media in production too (Django's static() helper only
    works in DEBUG)."""
    if settings.DEBUG:
        return django_serve(request, path, document_root=settings.MEDIA_ROOT)
    media_file = settings.MEDIA_ROOT / path
    if not media_file.exists():
        raise Http404("Not found.")
    return FileResponse(open(media_file, "rb"))


@csrf_exempt
def health_view(request):
    """Lightweight liveness probe for the API server, DB and Redis."""
    errors = []

    try:
        connection.ensure_connection()
        database = "connected"
    except Exception as exc:  # pragma: no cover - defensive
        database = "error"
        errors.append(f"database: {exc}")

    try:
        client = redis.Redis.from_url(settings.REDIS_URL)
        client.ping()
        redis_status = "connected"
    except Exception as exc:  # pragma: no cover - defensive
        redis_status = "error"
        errors.append(f"redis: {exc}")

    ok = database == "connected" and redis_status == "connected"

    payload = {
        "status": "ok" if ok else "degraded",
        "service": "GeoConnect API",
        "version": "0.1.0",
        "database": database,
        "redis": redis_status,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    if errors:
        payload["errors"] = errors

    return JsonResponse(payload, status=200 if ok else 503)