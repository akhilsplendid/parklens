import asyncio

from parklens.schemas import Child, Party
from parklens.services import planner, rules
from tests.conftest import FakeClient


def test_kb_rule_parsing(kb):
    g = kb.get("godistaget")
    assert g.min_height_cm == 100 and g.min_age == 4
    b = kb.get("skalmans-bilar")
    assert b.min_height_cm is None and b.min_age is None  # no limit with an adult
    assert b.solo_min_height_cm == 110 and b.solo_min_age == 5
    assert kb.find("Wildfire").id == "wildfire"
    assert kb.find("Lynx lynx").id == "lodjur"
    assert kb.find("amur tiger") is None  # no English names in the KB: Spark maps those


def test_height_rule_blocks_short_child(kb):
    party = Party(adults=2, children=[Child(name="Mia", age=5, height_cm=110)])
    e = rules.check(kb.get("wildfire"), party)
    assert not e.ok and e.blocked == ["Mia"] and "120 cm" in e.reason


def test_age_rule_blocks_young_child(kb):
    party = Party(adults=2, children=[Child(name="Bo", age=3, height_cm=105)])
    e = rules.check(kb.get("godistaget"), party)
    assert not e.ok and "4 years" in e.reason


def test_solo_threshold_applies_without_adult(kb):
    kid = Child(name="Ida", age=6, height_cm=105)
    with_adult = rules.check(kb.get("skalmans-bilar"), Party(adults=1, children=[kid]))
    alone = rules.check(kb.get("skalmans-bilar"), Party(adults=0, children=[kid]))
    assert with_adult.ok and not alone.ok


def test_plan_respects_budget_and_skips_blocked_rides(kb):
    party = Party(
        adults=2,
        children=[Child(name="Mia", age=5, height_cm=110)],
        interests=["big cats"],
        hours_available=2,
    )
    plan = planner.build_plan(kb, party)
    assert plan.total_minutes <= 120
    assert all(s.start for s in plan.stops)
    assert "wildfire" not in {s.item_id for s in plan.stops}
    assert {s.item_id for s in plan.skipped} == {"wildfire"}
    assert "Mia" in plan.skipped[0].why
    # Interest ranking puts the cats first.
    assert plan.stops[0].item_id in {"tiger", "lodjur"}
    assert all(s.source_url for s in plan.stops if s.kind != "break")


def test_plan_inserts_break_for_long_day(kb):
    party = Party(adults=2, children=[Child(name="Mia", age=5, height_cm=110)], hours_available=6)
    plan = planner.build_plan(kb, party)
    assert any(s.kind == "break" for s in plan.stops)


def test_replan_shortens_day_and_drops_done(kb):
    party = Party(adults=2, children=[Child(name="Mia", age=9, height_cm=135)], hours_available=6)
    plan = planner.build_plan(kb, party)
    done = [plan.stops[0].item_id]
    fresh = planner.replan(kb, plan, now="14:00", done_ids=done, hours_left=1, pace="relaxed")
    assert fresh.total_minutes <= 60
    assert done[0] not in {s.item_id for s in fresh.stops}
    assert fresh.stops[0].start == "14:00"


def test_narrate_plan_fills_why_from_model(kb):
    party = Party(adults=1, children=[Child(name="Mia", age=5, height_cm=110)], hours_available=1)
    plan = planner.build_plan(kb, party)
    first = plan.stops[0].item_id
    fake = FakeClient(
        {
            "PlanWhy": {
                "summary": "A cat-filled morning.",
                "stops": [{"item_id": first, "why": "Mia loves tigers."}],
            }
        }
    )
    out = asyncio.run(planner.narrate_plan(plan, kb, fake))
    assert out.summary == "A cat-filled morning." and out.stops[0].why == "Mia loves tigers."
    assert "ONLY the facts" in fake.calls[0][1][0]["content"]


def test_narration_failure_keeps_plan(kb):
    plan = planner.build_plan(kb, Party(hours_available=1))
    out = asyncio.run(planner.narrate_plan(plan, kb, FakeClient({})))  # no canned answer → raises
    assert out.stops and out.summary == ""
