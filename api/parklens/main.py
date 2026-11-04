"""ParkLens API."""

from __future__ import annotations

import base64
import json
import logging
import time
from collections import defaultdict, deque
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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from . import __version__, sam
from .config import Settings, get_settings
from .kb import KnowledgeBase
from .meta_client import HttpMetaClient, MetaAPIError, MetaClient
from .schemas import LensResult, Party, Plan, ReplanRequest
from .services import onboard, planner, timetravel
from .services.lens import LensService

log = logging.getLogger("parklens")

MAX_UPLOAD = 12 * 1024 * 1024
BILLED_PREFIXES = ("/lens", "/timetravel", "/plan", "/onboard", "/transcribe")


def settings(request: Request) -> Settings:
    return request.app.state.settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tests override `settings`; honour that here too so they never touch real data or keys.
    s = app.dependency_overrides.get(settings, get_settings)()
    app.state.settings = s
    path = s.kb_path if s.kb_path.exists() else s.kb_sample_path
    if path != s.kb_path:
        log.warning("generated KB missing; using the committed sample %s", path)
    app.state.kb = KnowledgeBase.load(path)
    app.state.client = HttpMetaClient(s)
    app.state.lens = LensService(app.state.kb, app.state.client, s)
    app.state.hits = defaultdict(deque)  # ip -> timestamps of billed requests
    log.info("loaded %d items for %s", len(app.state.kb.items), app.state.kb.park)
    yield
    await app.state.client.aclose()


app = FastAPI(title="ParkLens API", version=__version__, lifespan=lifespan)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Tiny per-IP limiter on the routes that call the Meta API. In-memory: fine for one VM."""
    if request.method == "POST" and request.url.path.startswith(BILLED_PREFIXES):
        s: Settings = request.app.state.settings
        client_host = request.client.host if request.client else "?"
        ip = request.headers.get("fly-client-ip") or client_host
        q: deque = request.app.state.hits[ip]
        now = time.time()
        while q and now - q[0] > 86400:
            q.popleft()
        last_minute = sum(1 for t in q if now - t < 60)
        if last_minute >= s.rate_limit_per_minute or len(q) >= s.rate_limit_per_day:
            detail = "Too many requests; try again in a minute."
            return JSONResponse({"error": "rate_limited", "detail": detail}, status_code=429)
        q.append(now)
    return await call_next(request)


app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def kb(request: Request) -> KnowledgeBase:
    return request.app.state.kb


def client(request: Request) -> MetaClient:
    return request.app.state.client


def lens(request: Request) -> LensService:
    return request.app.state.lens


@app.exception_handler(MetaAPIError)
async def meta_error(_: Request, exc: MetaAPIError):
    status = 503 if exc.status in (429, 504) else 502
    return JSONResponse(status_code=status, content={"error": "model_api", "detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error(_: Request, exc: ValidationError):
    """Model output or a form field that doesn't fit our schema is a 422, not a crash."""
    return JSONResponse(status_code=422, content={"error": "invalid", "detail": exc.errors()[:5]})


@app.exception_handler(sam.BadImage)
async def bad_image(_: Request, exc: sam.BadImage):
    return JSONResponse(status_code=415, content={"error": "bad_image", "detail": str(exc)})


async def read_upload(f: UploadFile) -> bytes:
    """Read an upload with a size cap, checking Content-Length before buffering."""
    if f.size is not None and f.size > MAX_UPLOAD:
        raise HTTPException(413, "file too large")
    data = await f.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "file too large")
    return data


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
        await read_upload(audio), audio.content_type or "audio/webm", c, s.default_language
    )
    return {"transcript": text, "party": party}


@app.post("/transcribe")
async def transcribe(c: Annotated[MetaClient, Depends(client)], audio: UploadFile = File(...)):
    text = await c.transcribe(await read_upload(audio), mime=audio.content_type or "audio/webm")
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
        here_id=body.here_id,
        prefer=params.get("prefer"),
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
    return await svc.analyze(await read_upload(image), p, hint, language, expected)


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
    s: Annotated[Settings, Depends(settings)],
    image: UploadFile = File(...),
    mode: str = Form("wild"),
    species_id: str | None = Form(None),
    box: str | None = Form(None, description="the SAM box from /lens, as JSON"),
):
    """Muse Image repaints the animal. When the Lens box is passed, the box (with padding) is
    what gets repainted, so the ancestor is the tiger, not the fence."""
    item = kb.get(species_id) if species_id else None
    data = await read_upload(image)
    b = None
    if box:
        try:
            d = json.loads(box)
            x1, y1, x2, y2, w, h = (int(d[k]) for k in ("x1", "y1", "x2", "y2", "w", "h"))
            b = sam.Box(0, x1, y1, x2, y2, w, h)
        except (ValueError, KeyError, TypeError) as e:
            raise HTTPException(400, f"bad box: {e}") from e
    try:
        if b is not None and 0.02 < b.area_fraction < 0.6:
            frame = sam.crop(data, b, pad=0.35, max_side=1024)
        else:
            frame, _ = sam.downscale(data, s.max_image_side)
        out = await timetravel.time_travel(frame, item, mode, c, "image/jpeg")
    except sam.BadImage:
        raise
    except ValueError as e:  # bad mode, or a box outside the frame
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
    too_long = any(isinstance(v, str) and len(v) > 64 for v in ev.props.values())
    if len(ev.name) > 40 or len(ev.props) > 12 or too_long:
        raise HTTPException(400, "event too large")
    line = {"t": int(time.time()), "name": ev.name, **{f"p_{k}": v for k, v in ev.props.items()}}
    try:
        s.events_path.parent.mkdir(parents=True, exist_ok=True)
        with s.events_path.open("a", encoding="utf8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError:
        log.warning("could not write event")
    return None
