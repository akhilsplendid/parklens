from __future__ import annotations

import json
from pathlib import Path

import pytest

from parklens.kb import KnowledgeBase

FIXTURE_KB = {
    "park": "Testpark",
    "items": [
        {
            "id": "tiger",
            "kind": "animal",
            "name": "Amurtiger",
            "scientific_name": "Panthera tigris altaica",
            "text_sv": "Amurtigern är världens största kattdjur. Här bor de: skogarna längs Amurfloden. Starkt hotad art.",
            "source_url": "https://example.test/djur/tiger",
            "image": "https://img.test/tiger.jpg",
            "headings": [],
        },
        {
            "id": "lodjur",
            "kind": "animal",
            "name": "Lodjur",
            "scientific_name": "Lynx lynx",
            "text_sv": "Lodjuret är Sveriges enda vilda kattdjur.",
            "source_url": "https://example.test/djur/lodjur",
            "headings": [],
        },
        {
            "id": "delfin",
            "kind": "animal",
            "name": "Delfin",
            "scientific_name": "Tursiops truncatus",
            "text_sv": "Delfiner lever i grupp.",
            "source_url": "https://example.test/djur/delfin",
            "headings": [],
        },
        {
            "id": "wildfire",
            "kind": "attraction",
            "name": "Wildfire på Testpark",
            "text_sv": "Berg- och dalbana. Längdkrav: Minst 120 cm",
            "height_requirement": "Minst 120 cm",
            "min_height_cm": 120,
            "source_url": "https://example.test/attr/wildfire",
            "headings": [],
        },
        {
            "id": "godistaget",
            "kind": "attraction",
            "name": "Godiståget på Testpark",
            "text_sv": "Tåg för barn.",
            "height_requirement": "Barn från 100 cm och 4 år åker i vuxet sällskap (15 år och äldre).",
            "min_height_cm": 100,
            "source_url": "https://example.test/attr/godistaget",
            "headings": [],
        },
        {
            "id": "skalmans-bilar",
            "kind": "attraction",
            "name": "Skalmans Bilar på Testpark",
            "text_sv": "Bilar.",
            "height_requirement": "Ingen längdgräns i vuxet sällskap, minst 110 cm & 5 år utan vuxen",
            "min_height_cm": 110,
            "source_url": "https://example.test/attr/bilar",
            "headings": [],
        },
    ],
}


@pytest.fixture
def kb(tmp_path: Path) -> KnowledgeBase:
    p = tmp_path / "kb.json"
    p.write_text(json.dumps(FIXTURE_KB), encoding="utf-8")
    return KnowledgeBase.load(p)


class FakeClient:
    """Scripted Meta client: returns canned JSON per schema name, records calls."""

    def __init__(self, answers: dict | None = None, sam_raw: str = ""):
        self.answers = answers or {}
        self.sam_raw = sam_raw
        self.calls: list[tuple[str, object]] = []

    async def chat_text(self, messages, *, model=None):
        self.calls.append(("chat_text", messages))
        return "ok"

    async def chat_json(self, messages, schema, *, name="Result", model=None):
        self.calls.append((name, messages))
        if name not in self.answers:
            raise AssertionError(f"no canned answer for {name}")
        return self.answers[name]

    async def sam_segment(self, image, prompt, *, mime="image/jpeg"):
        self.calls.append(("sam", prompt))
        return self.sam_raw

    async def image_edit(self, image, prompt, *, mime="image/jpeg"):
        self.calls.append(("image_edit", prompt))
        return b"\xff\xd8fakejpeg"

    async def transcribe(self, audio, *, mime="audio/webm"):
        self.calls.append(("transcribe", mime))
        return "two adults and a five year old called Mia, she is 110 centimetres, we love tigers"
