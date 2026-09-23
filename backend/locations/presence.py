"""GeoConnect presence: Redis-backed online tracking per room.

Keeps a SET of online user ids per room (key: presence:room:<id>).
Persistent data stays in PostgreSQL; only ephemeral online state lives in Redis.
"""

import redis
from django.conf import settings

_client = None

MEMBERSHIP_MAX = 60 * 60  # 1 hour TTL, refreshed on activity


def _get_client():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def mark_online(room_id, user_id):
    key = f"presence:room:{room_id}"
    try:
        pipe = _get_client().pipeline()
        pipe.sadd(key, user_id)
        pipe.expire(key, MEMBERSHIP_MAX)
        pipe.execute()
    except Exception:
        pass


def mark_offline(room_id, user_id):
    key = f"presence:room:{room_id}"
    try:
        _get_client().srem(key, user_id)
    except Exception:
        pass


def online_user_ids(room_id):
    key = f"presence:room:{room_id}"
    try:
        return {int(uid) for uid in _get_client().smembers(key)}
    except Exception:
        return set()