"""Voice/text onboarding: what the family says → a Party profile (structured output)."""

from __future__ import annotations

from ..meta_client import MetaClient
from ..schemas import PARTY_SCHEMA, Party

SYSTEM = (
    "Extract the visiting group from what the visitor said. Children need age and height in cm; "
    "if a height is missing, estimate from age (3y≈95, 5y≈110, 7y≈122, 9y≈133, 11y≈145) and keep "
    "the name they used or 'child 1', 'child 2'. Interests are short English tags. "
    "hours_available defaults to 6, language to the language they spoke, pace to 'normal', "
    "start_time to '10:00'."
)


async def extract_party(text: str, client: MetaClient, default_language: str = "en") -> Party:
    data = await client.chat_json(
        [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"Visitor said: {text}\nDefault language: {default_language}",
            },
        ],
        PARTY_SCHEMA,
        name="Party",
    )
    return Party.model_validate(data)


async def transcribe_and_extract(
    audio: bytes, mime: str, client: MetaClient, default_language: str = "en"
) -> tuple[str, Party]:
    text = await client.transcribe(audio, mime=mime)
    return text, await extract_party(text, client, default_language)
