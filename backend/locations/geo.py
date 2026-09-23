"""GeoConnect: geographic helpers (haversine distance, formatting)."""

import math


def haversine_meters(lat1, lon1, lat2, lon2):
    """Great-circle distance between two coordinates in meters."""
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def format_distance(meters):
    """Human friendly distance: '120 m' / '1.2 km'."""
    if meters < 1000:
        return f"{round(meters)}m away"
    return f"{round(meters / 1000, 1)}km away"