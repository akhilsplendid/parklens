"""Walking distances between park points (haversine, metres) and a kids-pace walk time."""

from __future__ import annotations

import math

KIDS_WALK_M_PER_MIN = 55  # a family with a 5-year-old, with stops


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def walk_minutes(m: float) -> int:
    return max(1, round(m / KIDS_WALK_M_PER_MIN)) if m > 40 else 0
