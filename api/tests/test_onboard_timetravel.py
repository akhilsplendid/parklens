import asyncio

from parklens.services import onboard, timetravel
from tests.conftest import FakeClient

PARTY = {
    "adults": 2,
    "children": [{"name": "Mia", "age": 5, "height_cm": 110}],
    "interests": ["big cats"],
    "hours_available": 6,
    "language": "en",
    "pace": "normal",
    "start_time": "10:00",
}


def test_voice_onboarding_round_trip():
    fake = FakeClient({"Party": PARTY})
    text, party = asyncio.run(onboard.transcribe_and_extract(b"audio", "audio/webm", fake))
    assert "Mia" in text and party.children[0].height_cm == 110 and party.interests == ["big cats"]
    assert fake.calls[0][0] == "transcribe"


def test_time_travel_prompt_uses_park_habitat(kb):
    fake = FakeClient()
    out = asyncio.run(timetravel.time_travel(b"img", kb.get("tiger"), "wild", fake))
    assert out.startswith(b"\xff\xd8")
    prompt = fake.calls[0][1]
    assert "Amurtiger" in prompt and "Amurfloden" in prompt and "no text" in prompt


def test_time_travel_rejects_bad_mode(kb):
    try:
        asyncio.run(timetravel.time_travel(b"img", None, "yesterday", FakeClient()))
    except ValueError as e:
        assert "mode" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_events_append(tmp_path):
    from fastapi.testclient import TestClient

    from parklens.config import Settings
    from parklens.main import app
    from parklens.main import settings as settings_dep

    path = tmp_path / "ev.jsonl"
    app.dependency_overrides[settings_dep] = lambda: Settings(model_api_key="x", events_path=path)
    try:
        with TestClient(app, raise_server_exceptions=True) as c:
            r = c.post(
                "/events", json={"name": "lens_hit", "props": {"species": "tiger", "ms": 1200}}
            )
            assert r.status_code == 204
            r = c.post("/events", json={"name": "x" * 41})
            assert r.status_code == 400
    finally:
        app.dependency_overrides.pop(settings_dep, None)
    lines = path.read_text().splitlines()
    assert len(lines) == 1 and '"p_species": "tiger"' in lines[0]
