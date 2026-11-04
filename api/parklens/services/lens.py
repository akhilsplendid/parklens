"""The Lens: camera frame → SAM 3.1 (box: is there an animal, where) in parallel with
Muse Spark (which of the park's listed species) → narration from the park's own text, with a
source link. The SAM box is drawn on the phone and is what Muse Image repaints in time travel.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict

from .. import sam
from ..config import Settings
from ..kb import KnowledgeBase
from ..meta_client import MetaClient, data_url
from ..schemas import LensResult, Party

log = logging.getLogger(__name__)

MAX_WARM = 12  # a day plan has ~8 animals; anything more is someone probing the endpoint

ID_SCHEMA = {
    "type": "object",
    "properties": {
        "species_id": {"type": "string", "description": "an id from the list, or 'none'"},
        "confidence": {"type": "number"},
        "what_i_see": {"type": "string"},
    },
    "required": ["species_id", "confidence", "what_i_see"],
}

NARRATE_SCHEMA = {
    "type": "object",
    "properties": {"narration": {"type": "string"}, "fun_fact": {"type": "string"}},
    "required": ["narration", "fun_fact"],
}


def _audience(party: Party | None) -> str:
    if party and party.youngest_age is not None and party.youngest_age <= 8:
        return f"a curious {party.youngest_age}-year-old (simple words, 3 short sentences, playful)"
    if party and party.youngest_age is not None:
        return f"a {party.youngest_age}-year-old (clear, 4 sentences, one wow fact)"
    return "an adult visitor (4 sentences, specific facts)"


def _prior(kb: KnowledgeBase, expected: str | None) -> str:
    """The visitor marked where they are on the map: a prior for the ID, not an override."""
    item = kb.get(expected) if expected else None
    if not item:
        return ""
    return (
        f"\n\nThe visitor says they are standing at the {item.short_name} ({item.id}) enclosure. "
        "Prefer that id if the image is consistent with it, but trust what you see."
    )


class LensService:
    def __init__(
        self, kb: KnowledgeBase, client: MetaClient, settings: Settings, cache_size: int = 256
    ):
        self.kb, self.client, self.s = kb, client, settings
        self._cache: OrderedDict[str, LensResult] = OrderedDict()
        self._narration_cache: OrderedDict[str, tuple[str, str]] = OrderedDict()
        self._cache_size = cache_size

    async def analyze(
        self,
        image: bytes,
        party: Party | None = None,
        hint: str | None = None,
        language: str | None = None,
        expected: str | None = None,
    ) -> LensResult:
        lang = language or (party.language if party else self.s.default_language)
        frame, mime = sam.downscale(image, self.s.max_image_side)
        key = hashlib.sha1(frame + f"|{lang}|{_audience(party)}|{expected}".encode()).hexdigest()
        if key in self._cache:
            r = self._cache[key].model_copy()
            r.cached = True
            return r

        # 1 + 2 in parallel: SAM 3.1 finds the animal while Muse Spark names it from the
        # park's species list. Both see the same downscaled frame, so the two calls overlap
        # and the Lens answers in two round trips instead of three.
        sam_task = asyncio.create_task(self.client.sam_segment(frame, hint or "animal", mime=mime))
        id_task = asyncio.create_task(
            self.client.chat_json(
                [
                    {
                        "role": "system",
                        "content": (
                            f"You identify animals at {self.kb.park}. Pick the best matching id "
                            "from this list, or 'none' if no listed species fits. Be honest "
                            "about confidence.\n"
                            + self.kb.catalogue("animal")
                            + _prior(self.kb, expected)
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Which listed species is this?"},
                            {"type": "image_url", "image_url": {"url": data_url(frame, mime)}},
                        ],
                    },
                ],
                ID_SCHEMA,
                name="SpeciesId",
            )
        )
        try:
            raw, ident = await asyncio.gather(sam_task, id_task)
        except BaseException:
            for t in (sam_task, id_task):  # don't keep billing the survivor
                t.cancel()
            raise
        boxes = sam.parse_boxes(raw)
        box = sam.largest(boxes)
        if box is None or box.area_fraction < 0.005:
            miss = LensResult(
                found=False,
                language=lang,
                narration="I can't spot an animal yet. Try getting closer or hold still.",
            )
            self._remember(self._cache, key, miss)  # same frame again → no second bill
            return miss

        item = self.kb.get(ident.get("species_id", "none"))
        box_dict = {
            "x1": box.x1,
            "y1": box.y1,
            "x2": box.x2,
            "y2": box.y2,
            "w": box.width,
            "h": box.height,
            "n_found": len(boxes),
        }
        if item is None:
            unknown = LensResult(
                found=True,
                box=box_dict,
                language=lang,
                confidence=ident.get("confidence"),
                narration=f"I see {ident.get('what_i_see', 'an animal').rstrip('. ')}, "
                f"but it isn't one of {self.kb.park}'s listed species.",
            )
            self._remember(self._cache, key, unknown)
            return unknown

        narration, fun = await self._narrate(item, party, lang)

        result = LensResult(
            found=True,
            species_id=item.id,
            species_name=item.short_name,
            scientific_name=item.scientific_name,
            confidence=ident.get("confidence"),
            box=box_dict,
            narration=narration,
            fun_fact=fun,
            source_url=item.source_url,
            language=lang,
        )
        self._remember(self._cache, key, result)
        return result

    async def _narrate(self, item, party: Party | None, lang: str) -> tuple[str, str]:
        """Narration from the park's own text only, cached per species + audience + language."""
        nkey = f"{item.id}|{lang}|{_audience(party)}"
        if nkey in self._narration_cache:
            return self._narration_cache[nkey]
        n = await self.client.chat_json(
            [
                {
                    "role": "system",
                    "content": (
                        f"You are a friendly guide at {self.kb.park}, talking to "
                        f"{_audience(party)}. Write in language code '{lang}'. Use ONLY the "
                        "park text below; never invent numbers. No medical or political "
                        "content.\n\nPARK TEXT:\n" + item.facts()
                    ),
                },
                {
                    "role": "user",
                    "content": f"We're looking at the {item.short_name} right now. "
                    "Tell us about it, then one fun fact.",
                },
            ],
            NARRATE_SCHEMA,
            name="Narration",
        )
        pair = (n["narration"], n["fun_fact"])
        self._remember(self._narration_cache, nkey, pair)
        return pair

    async def warm(self, party: Party | None, species_ids: list[str], language: str | None = None):
        """Pre-generate narration for the animals on today's plan so the first look is instant."""
        lang = language or (party.language if party else self.s.default_language)
        seen: dict[str, object] = {}
        for x in species_ids[:40]:
            i = self.kb.get(x)
            if i and i.kind == "animal" and i.id not in seen:
                seen[i.id] = i
        items = list(seen.values())[:MAX_WARM]

        async def one(item):
            try:
                await self._narrate(item, party, lang)
            except Exception as exc:  # best effort
                log.warning("warm %s failed: %s", item.id, exc)

        await asyncio.gather(*(one(i) for i in items))
        return len(items)

    def _remember(self, cache: OrderedDict, key: str, value) -> None:
        cache[key] = value
        if len(cache) > self._cache_size:
            cache.popitem(last=False)
