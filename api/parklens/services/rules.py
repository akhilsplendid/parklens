"""Ride eligibility. Hard rules live here, in code, never in the prompt."""

from __future__ import annotations

from ..kb import Item
from ..schemas import Eligibility, Party

ADULT_COMPANION_AGE = 15


def check(item: Item, party: Party) -> Eligibility:
    """Can everyone in the party do this item? Animals are always fine."""
    if item.kind != "attraction" or not party.children:
        return Eligibility(ok=True)

    has_adult = party.adults > 0 or any(c.age >= ADULT_COMPANION_AGE for c in party.children)
    blocked: list[str] = []
    reasons: set[str] = set()

    for child in party.children:
        # With an adult the companion thresholds apply; alone, the stricter solo ones.
        height_min, age_min = item.min_height_cm, item.min_age
        if not has_adult:
            height_min = item.solo_min_height_cm or height_min
            age_min = item.solo_min_age or age_min
        if height_min and child.height_cm < height_min:
            blocked.append(child.name)
            reasons.add(f"min {height_min} cm")
            continue
        if age_min and child.age < age_min:
            blocked.append(child.name)
            reasons.add(f"min {age_min} years")

    if blocked:
        return Eligibility(ok=False, blocked=blocked, reason=", ".join(sorted(reasons)))
    return Eligibility(ok=True)
