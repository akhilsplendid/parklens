"""Day planner: deterministic selection and scheduling, the model only writes the words.

Why not let the model plan? Benchmarks show LLMs rarely satisfy several hard constraints at
once (TravelPlanner, 2024). Height rules, ages and time budget are enforced here; Muse Spark is
asked afterwards for a one-line 'why' per stop and a summary in the family's language.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .. import geo
from ..kb import Item, KnowledgeBase
from ..meta_client import MetaClient
from ..schemas import Party, Plan, Stop
from . import rules

log = logging.getLogger(__name__)

STOP_MINUTES = {"animal": 20, "attraction": 30, "break": 30}
PACE_FACTOR = {"relaxed": 1.3, "normal": 1.0, "packed": 0.8}
BREAK_EVERY_MIN = 90  # kids need a sit-down roughly every hour and a half

# Interest words → kb search queries (Swedish text in the KB). Unknown interests search as-is.
INTEREST_QUERIES = {
    "big cats": "tiger lejon lodjur snöleopard kattdjur",
    "cats": "tiger lejon lodjur snöleopard",
    "monkeys": "gorilla schimpans gibbon apor",
    "apes": "gorilla schimpans gibbon",
    "rides": "berg- och dalbana karusell åktur",
    "roller coaster": "berg- och dalbana",
    "dolphins": "delfin",
    "elephants": "elefant",
    "giraffes": "giraff",
    "bears": "björn",
    "birds": "fågel papegoja falk struts",
    "endangered": "utrotningshotad starkt hotad",
    "bamse": "bamse skalman",
}


def _hhmm(t: datetime) -> str:
    return t.strftime("%H:%M")


def _rank_items(kb: KnowledgeBase, party: Party) -> tuple[list[Item], list[Item]]:
    """Return (animals, attractions) ordered by relevance to the party's interests."""
    score: dict[str, float] = {i.id: 0.0 for i in kb.items}
    for interest in party.interests:
        q = INTEREST_QUERIES.get(interest.lower().strip(), interest)
        for rank, item in enumerate(kb.search(q, limit=8)):
            score[item.id] += 10 - rank
    # Mild default preferences: flagship animals and rides first for kids.
    for i in kb.items:
        if i.image:
            score[i.id] += 0.5
        if i.kind == "attraction" and party.children:
            score[i.id] += 1.0
    animals = sorted(kb.animals, key=lambda i: -score[i.id])
    attractions = sorted(kb.attractions, key=lambda i: -score[i.id])
    return animals, attractions


def build_plan(
    kb: KnowledgeBase,
    party: Party,
    entrance: tuple[float, float] | None = None,
    prefer: str | None = None,
) -> Plan:
    """`prefer` ("rides" | "animals") is a re-plan hint that changes how the two kinds are
    interleaved; rules and the time budget are the same either way."""
    budget = int(party.hours_available * 60)
    factor = PACE_FACTOR[party.pace]
    animals, attractions = _rank_items(kb, party)

    eligible, skipped = [], []
    for a in attractions:
        e = rules.check(a, party)
        (eligible if e.ok else skipped).append((a, e))

    # Interleave: animal, animal, ride, animal, animal, ride ... "Kids want more rides" flips
    # it to ride, ride, animal; "more animals" drops rides to one in four.
    rides = [a for a, _ in eligible]
    rounds = {
        "rides": [(rides, 2), (animals, 1)],
        "animals": [(animals, 3), (rides, 1)],
    }.get(prefer or "", [(animals, 2), (rides, 1)])
    queue: list[Item] = []
    pos = {id(animals): 0, id(rides): 0}
    while any(pos[id(lst)] < len(lst) for lst, _ in rounds):
        for lst, n in rounds:
            for _ in range(n):
                if pos[id(lst)] < len(lst):
                    queue.append(lst[pos[id(lst)]])
                    pos[id(lst)] += 1

    # Greedy fill: add stops in priority order, route them by walking distance from the
    # entrance (nearest neighbour) and keep each one only if the whole day still fits the
    # time budget including walking and breaks. A far-away detour that blows the budget is
    # skipped in favour of the next candidate, so tight budgets stay local.
    picked: list[Item] = []
    stops: list[Stop] = []
    for item in queue:
        trial = _route(picked + [item], entrance)
        trial_stops = _schedule(trial, party, factor, entrance)
        if sum(s.minutes + s.walk_minutes for s in trial_stops) <= budget:
            picked, stops = trial, trial_stops
    used = sum(s.minutes + s.walk_minutes for s in stops)

    skipped_stops = [
        Stop(
            item_id=a.id,
            kind="attraction",
            name=a.short_name,
            start="",
            minutes=0,
            why=f"Not for {', '.join(e.blocked)}: {e.reason}",
            source_url=a.source_url,
            eligibility=e,
        )
        for a, e in skipped
    ]
    return Plan(party=party, stops=stops, skipped=skipped_stops, total_minutes=used)


def _route(items: list[Item], entrance: tuple[float, float] | None) -> list[Item]:
    located = [i for i in items if i.lat is not None and i.lon is not None]
    unlocated = [i for i in items if i not in located]
    if not located:
        return items
    cur = entrance or (located[0].lat, located[0].lon)
    ordered: list[Item] = []
    remaining = located[:]
    while remaining:
        nxt = min(remaining, key=lambda i: geo.distance_m(cur[0], cur[1], i.lat, i.lon))
        ordered.append(nxt)
        remaining.remove(nxt)
        cur = (nxt.lat, nxt.lon)
    return ordered + unlocated


def _schedule(
    items: list[Item], party: Party, factor: float, entrance: tuple[float, float] | None
) -> list[Stop]:
    stops: list[Stop] = []
    t = datetime.strptime(party.start_time, "%H:%M")
    since_break = 0
    cur = entrance
    for item in items:
        walk = 0
        if cur and item.lat is not None:
            walk = geo.walk_minutes(geo.distance_m(cur[0], cur[1], item.lat, item.lon))
        if since_break >= BREAK_EVERY_MIN and party.children:
            stops.append(
                Stop(
                    item_id="break",
                    kind="break",
                    name="Break",
                    start=_hhmm(t),
                    minutes=30,
                    why="Snack and rest. Tired kids make for a short day.",
                )
            )
            t += timedelta(minutes=30)
            since_break = 0
        t += timedelta(minutes=walk)
        mins = int(STOP_MINUTES[item.kind] * factor)
        stops.append(
            Stop(
                item_id=item.id,
                kind=item.kind,
                name=item.short_name,
                start=_hhmm(t),
                minutes=mins,
                source_url=item.source_url,
                image=item.image,
                eligibility=rules.check(item, party),
                walk_minutes=walk,
                lat=item.lat,
                lon=item.lon,
            )
        )
        t += timedelta(minutes=mins)
        since_break += mins + walk
        if item.lat is not None:
            cur = (item.lat, item.lon)
    return stops


WHY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "stops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"item_id": {"type": "string"}, "why": {"type": "string"}},
                "required": ["item_id", "why"],
            },
        },
    },
    "required": ["summary", "stops"],
}


async def narrate_plan(plan: Plan, kb: KnowledgeBase, client: MetaClient | None) -> Plan:
    """Ask Muse Spark for one friendly sentence per stop plus a summary. Facts only from the KB."""
    if client is None:
        return plan
    lines = []
    for s in plan.stops:
        item = kb.get(s.item_id)
        facts = item.facts(500) if item else ""
        lines.append(f"- {s.item_id} | {s.name} | {s.start} | {facts}")
    kids = ", ".join(f"{c.name} ({c.age})" for c in plan.party.children) or "no children"
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a warm park guide at {kb.park}. Write in language code "
                f"'{plan.party.language}'. Use ONLY the facts given. One short sentence per stop "
                "saying why it's worth it for this family. No prices, no medical advice."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Family: {plan.party.adults} adults, kids: {kids}. "
                f"Interests: {', '.join(plan.party.interests) or 'general'}.\n"
                f"Stops:\n"
                + "\n".join(lines)
                + "\n\nReturn a why for every stop and a 2-sentence summary."
            ),
        },
    ]
    try:
        data = await client.chat_json(messages, WHY_SCHEMA, name="PlanWhy")
        whys = {
            str(d.get("item_id")): str(d.get("why") or "")
            for d in data.get("stops") or []
            if isinstance(d, dict)
        }
        summary = str(data.get("summary") or "")
    except Exception as exc:  # narration is optional; the plan itself is already valid
        log.warning("plan narration failed: %s", exc)
        return plan
    for s in plan.stops:
        if whys.get(s.item_id):
            s.why = whys[s.item_id]
    plan.summary = summary
    return plan


def replan(
    kb: KnowledgeBase,
    plan: Plan,
    now: str,
    done_ids: list[str],
    hours_left: float | None,
    pace: str | None = None,
    entrance: tuple[float, float] | None = None,
    here_id: str | None = None,
    prefer: str | None = None,
) -> Plan:
    """Rebuild the rest of the day from `now`, dropping done stops. Same rules, new budget.

    Model-extracted values (hours_left, pace) go through Party validation again, so a bad
    extraction ("pace": "tired") falls back to the old value instead of crashing."""
    update: dict = {"start_time": now}
    if hours_left is not None and 0 < hours_left <= 14:
        update["hours_available"] = hours_left
    if pace in PACE_FACTOR:
        update["pace"] = pace
    party = Party.model_validate(plan.party.model_copy(update=update).model_dump())
    done = set(done_ids)
    # Start from where the family is now: the place they tapped on the map, else the last
    # stop they marked done, else the entrance.
    here = entrance
    for s in plan.stops:
        if s.item_id in done and s.lat is not None:
            here = (s.lat, s.lon)
    at = kb.get(here_id) if here_id else None
    if at is not None and at.lat is not None:
        here = (at.lat, at.lon)
    # Build a fresh plan without the done stops: the planner re-ranks, re-routes and re-times.
    pruned = KnowledgeBase([i for i in kb.items if i.id not in done], park=kb.park)
    fresh = build_plan(pruned, party, here, prefer)
    return fresh


REPLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "hours_left": {"type": ["number", "null"]},
        "pace": {"type": ["string", "null"], "enum": ["relaxed", "normal", "packed", None]},
        "done_ids": {"type": "array", "items": {"type": "string"}},
        "prefer": {
            "type": ["string", "null"],
            "enum": ["rides", "animals", None],
            "description": "what they want more of now, if they said so",
        },
    },
    "required": ["hours_left", "pace", "done_ids", "prefer"],
}


async def parse_replan_utterance(utterance: str, plan: Plan, client: MetaClient) -> dict:
    """'We're tired, one hour left' → {hours_left: 1, pace: 'relaxed', done_ids: []}."""
    ids = ", ".join(s.item_id for s in plan.stops)
    messages = [
        {
            "role": "system",
            "content": (
                "Extract re-planning parameters from what a family at a park said. "
                "'tired' or 'slow down' → pace relaxed; 'one hour left' → hours_left 1; "
                "'more rides' → prefer rides; 'skip/seen the animals' → prefer rides and "
                "done_ids = the animal ids; 'more animals' → prefer animals. Unknown → null/empty."
            ),
        },
        {"role": "user", "content": f"Planned stop ids: {ids}\nFamily said: {utterance}"},
    ]
    try:
        out = await client.chat_json(messages, REPLAN_SCHEMA, name="Replan")
    except Exception as exc:  # the deterministic re-plan still runs with what we know
        log.warning("replan extraction failed: %s", exc)
        return _replan_fallback(utterance)
    return out if isinstance(out, dict) else {}


def _replan_fallback(utterance: str) -> dict:
    """Keyword version of the extraction, used when the model is unavailable."""
    u = utterance.lower()
    out: dict = {"hours_left": None, "pace": None, "done_ids": [], "prefer": None}
    for words, hours in (("one hour", 1), ("two hours", 2), ("half an hour", 0.5)):
        if words in u:
            out["hours_left"] = hours
    if any(w in u for w in ("tired", "trött", "slow")):
        out["pace"] = "relaxed"
    if "ride" in u or "åk" in u:
        out["prefer"] = "rides"
    if "more animals" in u or "fler djur" in u:
        out["prefer"] = "animals"
    return out
