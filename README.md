# ParkLens

A personalized, multimodal guide for wildlife and theme parks, built for the
Meta Global AI Developer Hackathon (Indie track). Demo park: Kolmården, Sweden.
Unofficial prototype; not affiliated with or endorsed by Kolmården.

- Say who's visiting (kids' ages and heights, interests, time) and get a day plan that
  respects ride height rules.
- Point the camera at an enclosure: SAM 3.1 finds the animal, Muse Spark tells its story
  from the park's own facts, and Muse Image shows it in its wild habitat or as its
  prehistoric ancestor.
- The plan adapts during the day as you go.

## How it uses Meta's models

| Step | Model | Endpoint |
|---|---|---|
| Voice onboarding | `muse-voice-transcribe-1.0` | `/v1/asr/transcribe` |
| Party profile, species ID, narration | `muse-spark-1.3` (structured output) | `/v1/chat/completions` |
| Find the animal in the frame | `sam-3.1` | `/v1/responses` (streamed) |
| Habitat / ancestor image | `muse-image-1.0` | `/v1/images/edits` |

```mermaid
flowchart LR
  subgraph Phone["Phone (Next.js PWA)"]
    V[🎙️ voice] --> O
    C[📷 camera] --> L
    O[Family profile] --> P[Day plan + map]
    P --> R[Re-plan]
  end
  subgraph API["FastAPI"]
    O -->|/onboard| T[Voice Transcribe] --> S1[Muse Spark<br/>structured output]
    P -->|/plan| PL[Planner<br/>rules + routing in code] --> S2[Muse Spark<br/>writes the words]
    L -->|/lens| SAM[SAM 3.1<br/>box + mask] & S3[Muse Spark<br/>species ID]
    SAM & S3 --> N[Narration<br/>from park text only]
    L -->|/timetravel| MI[Muse Image<br/>habitat / ancestor]
  end
  KB[(Park knowledge base<br/>50 animals, 11 rides,<br/>rules, GPS, sources)] --> PL & S3 & N
```

Hard rules (height, age, time) are enforced in code (`api/parklens/services/rules.py`);
the model only writes the words. Every narration is grounded in the park's own page and
returns its `source_url`.

## Quick start (Windows, PowerShell)

```powershell
copy .env.example .env               # then put your MODEL_API_KEY in .env
python scripts\extract_kb.py         # builds data\generated\kb.json from the local crawl
python scripts\smoke_test.py         # one real call: lists models, grounded tiger answer
cd api
uv venv; .venv\Scripts\activate
uv pip install -e ".[dev]"
pytest -q                            # 22 tests, no network needed
uvicorn parklens.main:app --reload   # http://127.0.0.1:8000/docs
```

Or with Docker: `docker compose up --build`.

## API

| Route | What it does |
|---|---|
| `GET /health` | KB loaded? |
| `GET /kb/items?kind=animal` | the park's animals / attractions with rules and sources |
| `POST /onboard/text` `{text}` | spoken/typed description → `Party` |
| `POST /onboard/voice` (audio file) | transcript + `Party` |
| `POST /plan` (`Party`) | day plan; rides the kids can't ride land in `skipped` with the reason |
| `POST /plan/replan` `{plan, utterance, now, done_ids}` | "we're tired, one hour left" → new plan |
| `GET /kb/map` | entrance and bounds for the schematic park map |
| `POST /lens` (image, party?, expected?, language?) | box + species + narration + source |
| `POST /lens/warm` `{party, species_ids}` | pre-generate narration for today's animals |
| `POST /transcribe` (audio file) | speech → text |
| `POST /timetravel` (image, mode=wild/ancestor/future, species_id) | AI artistic image |

## Layout

```
api/parklens/        FastAPI app, Meta client, SAM parser, geo, services (lens, planner, rules, ...)
api/tests/           pytest suite with a fake Meta client
web/                 Next.js PWA: family, plan, map, lens
scripts/extract_kb.py  builds the knowledge base from a local crawl of the park site
docs/PLAN.md         architecture, schedule, demo outline
```

## Data

Park facts come from a public, robots.txt-permitted crawl made before the hackathon.
That crawl and the generated knowledge base are not committed; only the extraction
script is. Every fact keeps its source URL. All application code was written during the
hackathon (Oct 27 – Nov 4, 2026).
