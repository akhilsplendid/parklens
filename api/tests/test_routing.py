from parklens.kb import Item, KnowledgeBase
from parklens.schemas import Party
from parklens.services import planner


def _item(i, lat, lon, kind="animal"):
    return Item(id=i, kind=kind, name=i, text_sv="", source_url=f"https://x/{i}", lat=lat, lon=lon)


def test_route_orders_by_walking_distance_and_adds_walk_minutes():
    # Entrance at (0,0); b is near, a is far east, c is far west. Priority order: a, b, c.
    kb = KnowledgeBase(
        [_item("a", 58.0, 16.010), _item("b", 58.0, 16.001), _item("c", 58.0, 15.992)], park="T"
    )
    party = Party(adults=1, hours_available=3, start_time="10:00")
    plan = planner.build_plan(kb, party, entrance=(58.0, 16.0))
    assert [s.item_id for s in plan.stops] == ["b", "a", "c"]
    assert plan.stops[0].walk_minutes <= 1  # ~60 m from the entrance
    assert plan.stops[1].walk_minutes >= 8  # ~530 m east at kids' pace
    assert plan.stops[2].walk_minutes >= 15  # back across the park
    assert plan.total_minutes == sum(s.minutes + s.walk_minutes for s in plan.stops)


def test_tight_budget_skips_far_detour():
    kb = KnowledgeBase([_item("far", 58.0, 16.05), _item("near", 58.0, 16.001)], park="T")
    party = Party(adults=1, hours_available=0.75, start_time="10:00")  # 45 min
    plan = planner.build_plan(kb, party, entrance=(58.0, 16.0))
    assert [s.item_id for s in plan.stops] == ["near"]
    assert plan.total_minutes <= 45


def test_unlocated_items_go_last():
    kb = KnowledgeBase(
        [
            Item(id="x", kind="animal", name="x", text_sv="", source_url="u"),
            _item("y", 58.0, 16.001),
        ],
        park="T",
    )
    plan = planner.build_plan(kb, Party(hours_available=2), entrance=(58.0, 16.0))
    assert [s.item_id for s in plan.stops] == ["y", "x"]
