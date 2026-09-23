"""
Health-check endpoints.

Used by the React frontend (and by `npm run dev` phase 1 verification) to
confirm that the API server is reachable and that PostgreSQL + Redis answer.
"""

from datetime import datetime, timezone

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


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