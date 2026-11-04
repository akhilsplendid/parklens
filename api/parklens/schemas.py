"""Request/response models shared by the API and the services."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


class Child(BaseModel):
    name: str = "child"
    age: int = Field(ge=0, le=17)
    height_cm: int = Field(ge=40, le=200)


class Party(BaseModel):
    adults: int = Field(default=2, ge=0, le=20)
    children: list[Child] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list, description="e.g. 'big cats', 'rides'")
    hours_available: float = Field(default=6, gt=0, le=14)
    language: str = Field(default="en", description="BCP-47-ish: en, sv, fi, de ...")
    pace: Literal["relaxed", "normal", "packed"] = "normal"
    start_time: str = Field(default="10:00", pattern=HHMM)

    @property
    def youngest_age(self) -> int | None:
        return min((c.age for c in self.children), default=None)


PARTY_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "adults": {"type": "integer"},
        "children": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "height_cm": {"type": "integer"},
                },
                "required": ["name", "age", "height_cm"],
            },
        },
        "interests": {"type": "array", "items": {"type": "string"}},
        "hours_available": {"type": "number"},
        "language": {"type": "string"},
        "pace": {"type": "string", "enum": ["relaxed", "normal", "packed"]},
        "start_time": {"type": "string"},
    },
    "required": [
        "adults",
        "children",
        "interests",
        "hours_available",
        "language",
        "pace",
        "start_time",
    ],
}


class Eligibility(BaseModel):
    ok: bool
    blocked: list[str] = Field(default_factory=list, description="child names who can't go")
    reason: str | None = None


class Stop(BaseModel):
    item_id: str
    kind: Literal["animal", "attraction", "break"]
    name: str
    start: str
    minutes: int
    why: str = ""
    source_url: str | None = None
    image: str | None = None
    eligibility: Eligibility | None = None
    walk_minutes: int = 0
    lat: float | None = None
    lon: float | None = None


class Plan(BaseModel):
    party: Party
    stops: list[Stop]
    skipped: list[Stop] = Field(default_factory=list, description="rides the kids can't ride")
    total_minutes: int
    summary: str = ""


class LensResult(BaseModel):
    found: bool
    species_id: str | None = None
    species_name: str | None = None
    scientific_name: str | None = None
    confidence: float | None = None
    box: dict | None = None
    narration: str = ""
    fun_fact: str = ""
    source_url: str | None = None
    language: str = "en"
    cached: bool = False


class ReplanRequest(BaseModel):
    plan: Plan
    utterance: str = Field(description="What the family said, e.g. 'we are tired, one hour left'")
    now: str = Field(default="13:00", pattern=HHMM)
    done_ids: list[str] = Field(default_factory=list)
    here_id: str | None = Field(default=None, description="item the family is standing at")
