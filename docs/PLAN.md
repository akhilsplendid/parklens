# ParkLens: plan

Track: Indie developer. Theme: Build for Your World.
Deadline: Wed Nov 4, 21:00 ET (Thu Nov 5, 03:00 Stockholm). Aim to submit Nov 4 evening CET.

## Judging fit

| Criterion (weight) | How ParkLens earns it |
|---|---|
| Impact (30%) | Families waste park days on queues, height-rule surprises and missed shows. Works for any park with a website. |
| Use of Meta tooling (25%) | Five models in one flow: Muse Spark, Muse Wonder, SAM 3.1, Muse Image, Voice Transcribe (+ Muse Glimmer stretch). |
| Technical depth (20%) | Grounded answers with citations, structured-output planner with hard constraints, video segmentation, tracing, tests. |
| Demo (25%) | Live camera on a tiger, a "1 million years ago" image, a plan that re-routes on stage. |

Bonus targets: Best Creative Build (Muse Image), Best Agentic Use-Case, Most Viral (post the before/after images on X).

## User flow

1. **Onboard by voice**: "Two adults, kids aged 5 and 9, 110 and 135 cm, love big cats, leave at 4."
   Voice Transcribe turns speech into text, then Muse Spark turns that text into a `Party` profile (structured output).
2. **Day plan**: the planner agent picks animals, rides and breaks. Height rules are hard
   constraints checked in code, not left to the model. Every stop cites its source page.
3. **Lens**: camera frame → SAM 3.1 (`"tiger"`, `"animal"`) → masks and boxes → crop → Muse Spark
   identifies the species against the knowledge base and narrates for the party (kid or adult level, in the chosen language).
4. **Time travel**: Muse Image edits the cropped animal into its wild habitat, or redraws it as its
   prehistoric ancestor. Shown as a before/after slider and saved to a "photo journal".
5. **Re-plan**: "We're tired, 1 hour left" or a skipped stop → Muse Wonder re-plans with tools.
6. **Journal**: at the end of the day, a shareable illustrated summary of the visit.

## Architecture

```
web (Next.js 15, TypeScript, PWA, camera + mic)
  │  REST + SSE
api (FastAPI, Python 3.12)
  ├─ /onboard    Voice Transcribe → Spark structured output → Party
  ├─ /plan       planner agent (Wonder, tool calls) + constraint checker
  ├─ /lens       SAM 3.1 segment → Spark vision ID + grounded narration
  ├─ /timetravel Muse Image edit
  └─ /journal
  ├─ kb: kb.json → Postgres + pgvector (facts, rides, height rules, zones)
  ├─ Redis: sessions, response cache (saves API credits)
  └─ OpenTelemetry traces → console / Jaeger
docker compose: api, web, postgres, redis.  CI: GitHub Actions (ruff, pytest, tsc, build)
```

Models (OpenAI-compatible endpoint `https://api.meta.ai/v1`):

| Job | Model |
|---|---|
| Fast vision ID, narration, profile extraction | `muse-spark-1.3` |
| Planner / re-planner agent with tools | `muse-wonder-1.0` |
| Segmentation (image + video) | `sam-3.1` via `/v1/responses` |
| Habitat / ancestor images | `muse-image-1.0` via `/v1/images/edits` |
| Speech to text (live) | `muse-voice-transcribe-1.0` (WebSocket) |
| Stretch: offline guide | Muse Glimmer, self-hosted |

## Schedule

| Day | Goal | Done when |
|---|---|---|
| Wed Oct 28 | Repo, knowledge-base extraction, API smoke test | `smoke_test.py` prints a grounded tiger answer |
| Thu Oct 29 | API skeleton, docker compose, Postgres KB load, `/lens` with SAM + Spark | Photo of a tiger → mask + correct, cited narration |
| Fri Oct 30 | `/timetravel` (Muse Image), web camera page, before/after slider | End-to-end Lens on a phone |
| Sat Oct 31 | Voice onboarding + `/plan` with height constraints, park zone map | Spoken party profile → valid plan |
| Sun Nov 1 | Re-planner agent, journal, Swedish/English | "1 hour left" re-plans correctly |
| Mon Nov 2 | Polish UI, caching, tracing, tests, CI, deploy (Fly.io or Render) | Public URL works on mobile |
| Tue Nov 3 | Feature freeze. Record the 3-minute demo, write the README, post on X | Video uploaded |
| Wed Nov 4 | Buffer, final checks, **submit** | Submission confirmed |

## 3-minute demo outline

0:00 the problem (a family at a park gate) → 0:20 voice onboarding → 0:45 plan with height rules
→ 1:15 Lens on the tiger: mask, narration for a 5-year-old → 1:50 "show me its ancestor"
→ 2:15 re-plan on "we're tired" → 2:40 journal + architecture slide → 3:00.

## Rules checklist

- [ ] Public repo; all code is new from Oct 27 onward (the scrape data is pre-existing; say so in the README)
- [ ] Don't commit the park's raw text or images; link to sources and show "Unofficial prototype"
- [ ] No medical, political or war content; it's not a plain image analyzer or a basic RAG app
- [ ] A 3-minute video that shows only hackathon-built work
- [ ] All teammates listed; submit on the CV platform

## Risks

- **You may not be able to film at the park (off-season, distance):** demo with photos/video on a screen, plus one
  recorded clip on site if possible.
- **API credits ($150):** cache every response in Redis, downscale camera frames, use Spark for everything except the planner.
- **Muse Image hallucinating a "real" ancestor:** label images as artistic and ground the ancestor's name in the facts text.
- **No ride map coordinates in the scrape:** hand-draw a simple zone graph (counts as new work).
