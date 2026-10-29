"""Thin async client for Meta Model API (OpenAI-compatible, base https://api.meta.ai/v1).

Services depend on the `MetaClient` protocol, so tests inject a fake and never hit the network.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Protocol

from .config import Settings


class MetaClient(Protocol):
    async def chat_text(self, messages: list[dict], *, model: str | None = None) -> str: ...

    async def chat_json(
        self, messages: list[dict], schema: dict, *, name: str = "Result", model: str | None = None
    ) -> dict: ...

    async def sam_segment(self, image: bytes, prompt: str, *, mime: str = "image/jpeg") -> str: ...

    async def image_edit(self, image: bytes, prompt: str, *, mime: str = "image/jpeg") -> bytes: ...

    async def transcribe(self, audio: bytes, *, mime: str = "audio/webm") -> str: ...


def data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


class HttpMetaClient:
    """Real client. One httpx.AsyncClient for the app lifetime."""

    def __init__(self, settings: Settings):
        import httpx  # imported here so the package loads without httpx for pure-logic tests

        self.s = settings
        self._http = httpx.AsyncClient(
            base_url=settings.model_api_base,
            headers={"Authorization": f"Bearer {settings.model_api_key}"},
            timeout=settings.request_timeout_s,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _post(self, path: str, body: dict, **kw: Any) -> Any:
        r = await self._http.post(path, json=body, **kw)
        if r.status_code >= 400:
            raise MetaAPIError(r.status_code, r.text[:500])
        return r.json()

    async def chat_text(self, messages: list[dict], *, model: str | None = None) -> str:
        data = await self._post(
            "/chat/completions", {"model": model or self.s.fast_model, "messages": messages}
        )
        return data["choices"][0]["message"]["content"]

    async def chat_json(
        self, messages: list[dict], schema: dict, *, name: str = "Result", model: str | None = None
    ) -> dict:
        data = await self._post(
            "/chat/completions",
            {
                "model": model or self.s.fast_model,
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": name, "schema": schema},
                },
            },
        )
        return json.loads(data["choices"][0]["message"]["content"])

    async def sam_segment(self, image: bytes, prompt: str, *, mime: str = "image/jpeg") -> str:
        """Returns SAM 3.1's raw special-token output text (boxes + masks)."""
        body = {
            "model": self.s.sam_model,
            "stream": True,
            "metadata": {"mask_encoding": "one_bit"},
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url(image, mime)},
                    ],
                }
            ],
        }
        chunks: list[str] = []
        async with self._http.stream("POST", "/responses", json=body) as r:
            if r.status_code >= 400:
                raise MetaAPIError(r.status_code, (await r.aread())[:500].decode(errors="ignore"))
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload in ("", "[DONE]"):
                    continue
                event = json.loads(payload)
                if event.get("type") == "response.output_text.delta":
                    chunks.append(event.get("delta", ""))
        return "".join(chunks)

    async def image_edit(self, image: bytes, prompt: str, *, mime: str = "image/jpeg") -> bytes:
        data = await self._post(
            "/images/edits",
            {
                "model": self.s.image_model,
                "prompt": prompt,
                "images": [{"image_url": data_url(image, mime)}],
                "n": 1,
                "output_format": "jpeg",
                "reasoning_strength": "low",
            },
        )
        return base64.b64decode(data["data"][0]["b64_json"])

    async def transcribe(self, audio: bytes, *, mime: str = "audio/webm") -> str:
        ext = mime.split("/")[-1]
        r = await self._http.post(
            "/asr/transcribe",
            data={"model": self.s.asr_model},
            files={"file": (f"audio.{ext}", audio, mime)},
        )
        if r.status_code >= 400:
            raise MetaAPIError(r.status_code, r.text[:500])
        data = r.json()
        return data.get("text") or data.get("transcript") or ""


class MetaAPIError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"Meta Model API {status}: {detail}")
        self.status = status
        self.detail = detail
