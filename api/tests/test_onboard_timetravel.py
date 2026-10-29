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
