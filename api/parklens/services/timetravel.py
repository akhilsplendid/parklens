"""Time travel: Muse Image redraws the animal in its wild habitat or as its ancient ancestor.

Images are labelled artistic; the ancestor name is pulled from the park text when present,
otherwise the prompt stays generic ("a prehistoric ancestor of the ...").
"""

from __future__ import annotations

from ..kb import Item
from ..meta_client import MetaClient

MODES = {
    "wild": (
        "Keep this exact animal, its pose and markings. Replace the zoo enclosure with its natural "
        "wild habitat: {habitat}. Photorealistic, golden hour, no fences, no people, no text."
    ),
    "ancestor": (
        "Reimagine this animal as its prehistoric ancestor from one million years ago, same pose "
        "and framing, in an Ice Age landscape. Natural-history illustration style, no text."
    ),
    "future": (
        "Show this exact animal thriving in a restored wild landscape 100 years from now, same "
        "pose, lush protected nature reserve, hopeful mood, no text."
    ),
}


def habitat_hint(item: Item) -> str:
    """Grab the 'Här bor de' / 'In the wild' paragraph if the park text has one."""
    text = item.text_sv
    for marker in ("Här bor de", "I världen", "lever i"):
        i = text.find(marker)
        if i >= 0:
            return text[i : i + 220]
    return "the species' natural wild habitat"


async def time_travel(
    image: bytes, item: Item | None, mode: str, client: MetaClient, mime: str = "image/jpeg"
) -> bytes:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {list(MODES)}")
    name = item.short_name if item else "animal"
    prompt = MODES[mode].format(habitat=habitat_hint(item) if item else "its natural habitat")
    prompt = f"Subject: {name}. " + prompt
    return await client.image_edit(image, prompt, mime=mime)
