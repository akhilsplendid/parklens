"""ParkLens API."""

from __future__ import annotations

import base64
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__
from .config import Settings, get_settings
from .kb import KnowledgeBase
from .meta_client import HttpMetaClient, MetaAPIError, MetaClient
from .schemas import LensResult, Party, Plan, ReplanRequest
from .services import onboard, planner, timetravel
from .services.lens import LensService

log = logging.getLogger("parklens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.settings = s
    app.state.kb = KnowledgeBase.load(s.kb_path)
    app.state.client = HttpMetaClient(s)
    app.state.lens = LensService(app.state.kb, app.state.client, s)
    log.info("loaded %d items for %s", len(app.state.kb.items), app.state.kb.park)
    yield
    await app.state.client.aclose()


app = FastAPI(title="ParkLens API", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def kb(request: Request) -> KnowledgeBase:
    return request.app.state.kb


def client(request: Request) -> MetaClient:
    return request.app.state.client


def lens(request: Request) -> LensService:
    return request.app.state.lens


def settings(request: Request) -> Settings:
    return request.app.state.settings


@app.exception_handler(MetaAPIError)
async def meta_error(_: Request, exc: MetaAPIError):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=502, content={"error": "model_api", "detail": str(exc)})


@app.get("/health")
async def health(kb: Annotated[KnowledgeBase, Depends(kb)]):
    return {
        "ok": True,
        "park": kb.park,
        "animals": len(kb.animals),
        "attractions": len(kb.attractions),
        "version": __version__,
    }


@app.get("/kb/items")
async def list_items(kb: Annotated[KnowledgeBase, Depends(kb)], kind: str | None = None):
    return [
        {
            "id": i.id,
            "kind": i.kind,
            "name": i.short_name,
            "scientific_name": i.scientific_name,
            "image": i.image,
            "source_url": i.source_url,
            "min_height_cm": i.min_height_cm,
            "height_requirement": i.height_requirement,
            "lat": i.lat,
            "lon": i.lon,
        }
        for i in kb.items
        if kind in (None, i.kind)
    ]


@app.get("/kb/map")
async def park_map(
    kb: Annotated[KnowledgeBase, Depends(kb)], s: Annotated[Settings, Depends(settings)]
):
    """Entrance and the bounding box of every located item, for drawing the park map."""
    pts = [i for i in kb.items if i.lat is not None]
    return {
        "park": kb.park,
        "entrance": {"lat": s.park_entrance_lat, "lon": s.park_entrance_lon},
        "bounds": {
            "min_lat": min(i.lat for i in pts),
            "max_lat": max(i.lat for i in pts),
            "min_lon": min(i.lon for i in pts),
            "max_lon": max(i.lon for i in pts),
        }
        if pts
        else None,
        "located": len(pts),
    }


class OnboardText(BaseModel):
    text: str


@app.post("/onboard/text", response_model=Party)
async def onboard_text(
    body: OnboardText,
    c: Annotated[MetaClient, Depends(client)],
    s: Annotated[Settings, Depends(settings)],
):
    return await onboard.extract_party(body.text, c, s.default_language)


@app.post("/onboard/voice")
async def onboard_voice(
    c: Annotated[MetaClient, Depends(client)],
    s: Annotated[Settings, Depends(settings)],
    audio: UploadFile = File(...),
):
    text, party = await onboard.transcribe_and_extract(
        await audio.read(), audio.content_type or "audio/webm", c, s.default_language
    )
    return {"transcript": text, "party": party}


@app.post("/transcribe")
async def transcribe(c: Annotated[MetaClient, Depends(client)], audio: UploadFile = File(...)):
    text = await c.transcribe(await audio.read(), mime=audio.content_type or "audio/webm")
    return {"text": text}


@app.post("/plan", response_model=Plan)
async def make_plan(
    party: Party,
    kb: Annotated[KnowledgeBase, Depends(kb)],
    c: Annotated[MetaClient, Depends(client)],
    s: Annotated[Settings, Depends(settings)],
    narrate: bool = True,
):
    plan = planner.build_plan(kb, party, (s.park_entrance_lat, s.park_entrance_lon))
    return await planner.narrate_plan(plan, kb, c if narrate else None)


@app.post("/plan/replan", response_model=Plan)
async def replan(
    body: ReplanRequest,
    kb: Annotated[KnowledgeBase, Depends(kb)],
    c: Annotated[MetaClient, Depends(client)],
    s: Annotated[Settings, Depends(settings)],
):
    params = await planner.parse_replan_utterance(body.utterance, body.plan, c)
    fresh = planner.replan(
        kb,
        body.plan,
        body.now,
        body.done_ids + list(params.get("done_ids") or []),
        params.get("hours_left"),
        params.get("pace"),
        (s.park_entrance_lat, s.park_entrance_lon),
    )
    return await planner.narrate_plan(fresh, kb, c)


@app.post("/lens", response_model=LensResult)
async def lens_analyze(
    svc: Annotated[LensService, Depends(lens)],
    image: UploadFile = File(...),
    party: str | None = Form(None),
    hint: str | None = Form(None),
    language: str | None = Form(None),
    expected: str | None = Form(None),
):
    p = Party.model_validate_json(party) if party else None
    data = await image.read()
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "image too large")
    return await svc.analyze(data, p, hint, language, expected)


class WarmRequest(BaseModel):
    party: Party | None = None
    species_ids: list[str]


@app.post("/lens/warm")
async def lens_warm(
    body: WarmRequest, tasks: BackgroundTasks, svc: Annotated[LensService, Depends(lens)]
):
    tasks.add_task(svc.warm, body.party, body.species_ids)
    return {"scheduled": len(body.species_ids)}


@app.post("/timetravel")
async def time_travel(
    kb: Annotated[KnowledgeBase, Depends(kb)],
    c: Annotated[MetaClient, Depends(client)],
    image: UploadFile = File(...),
    mode: str = Form("wild"),
    species_id: str | None = Form(None),
):
    item = kb.get(species_id) if species_id else None
    try:
        out = await timetravel.time_travel(
            await image.read(), item, mode, c, image.content_type or "image/jpeg"
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return {
        "mode": mode,
        "species_id": species_id,
        "label": "AI-generated artistic impression",
        "image_b64": base64.b64encode(out).decode(),
        "mime": "image/jpeg",
    }


class Event(BaseModel):
    """Anonymous product event from the web app (no ids, no text, no images)."""

    name: str  # e.g. plan_made, lens_hit, lens_miss, timetravel, replan, share
    props: dict[str, str | int | float | bool] = {}


@app.post("/events", status_code=204)
async def log_event(ev: Event, s: Annotated[Settings, Depends(settings)]):
    """Append one line to a local JSONL file so we can count what judges and testers use.
    Nothing personal is accepted: only a short event name and flat scalar props."""
    if len(ev.name) > 40 or len(ev.props) > 12:
        raise HTTPException(400, "event too large")
    line = {"t": int(time.time()), "name": ev.name, **{f"p_{k}": v for k, v in ev.props.items()}}
    try:
        s.events_path.parent.mkdir(parents=True, exist_ok=True)
        with s.events_path.open("a", encoding="utf8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        log.warning("could not write event")
    return None
