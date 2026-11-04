# Status (Nov 4, morning — deadline 03:00 Stockholm time tonight)

## Review round (three critic passes + one verification pass, all fixed and committed)
- API: per-IP rate limit (20/min, 400/day) on billed routes, upload caps, EXIF rotation,
  decompression-bomb cap, 415/422/429/503 instead of 500s, one retry on 429/5xx, re-plan
  re-validates model output and has a keyword fallback, `here_id` + `prefer` (rides/animals)
  so every re-plan chip does something, time travel repaints the SAM box, misses cached,
  warm capped, `data/kb.sample.json` so a fresh clone boots. 28 tests.
- Web: iOS voice (mp4 recorder) and speech unlock, second camera capture works, gallery
  photos rotated + shrunk on the phone, share feedback, touch targets, map labels, demo
  clock always labelled, error boundary, PNG home-screen icons.
- Docs: four models (not five), PLAN.md marked as the day-1 plan, sign statistic sourced
  (Spooner et al. 2024), README explains computed vs generated and why the Lens is not RAG.

## Previous status (Oct 29)

## Done and verified against the real Meta API
- Voice/text onboarding → family profile (structured output)
- Day plan: interest ranking, height/age rules in code, breaks, GPS routing with walking
  times (55 of 61 places located; dolphins pinned by hand next to Delfinexpressen), re-plan from speech
- Lens: SAM 3.1 box + Muse Spark species ID (in parallel) + narration from park text,
  cached per species/audience/language and pre-warmed when a plan is made
- Time travel (wild / ancestor / future) with before/after slider and a share card for X
- Map tab: schematic park map with today's numbered route and "I'm here" demo mode
- Design pass: cream/forest/amber palette, Nunito, welcome carousel with three Higgsfield
  illustrations (`web/public/art/*.webp`), lens-ring + paw app icon (`web/public/icon.svg`),
  motion on the Lens box and page transitions
- `POST /events`: anonymous usage counter (plan_made, lens_hit/miss, timetravel, replan, share)
  written to `data/generated/events.jsonl`, so we can quote real numbers in the pitch
- Demo clock on the Plan tab (tap the time line: real → 13:00 → 15:00 → 17:00) for the re-plan shot
- 23 backend tests, ruff clean; web builds clean (tsc + eslint)
- Docker (api + web), Fly.io config, deploy guide, demo script, README with architecture
- CI builds and lints the web app as well as the API
- Two Higgsfield clips for the video (opening shot 9:16, tiger 16:9 to point the Lens at): links in docs/DEMO.md
- docs/SUBMISSION.md: text for the hackathon form, ready to paste after deploy
- Full stack smoke-tested again today from the Linux VM against the real API: plan now starts at the dolphins (1 min from the gate), Wildfire and Sjörövarskeppet skipped for Mia, /events writes

## Evening checklist (you)
1. `cd web && npm install` once on Windows (lucide-react, framer-motion were added), then
   `npm run dev`; restart `uvicorn` so the new `/events` route and the dolphin pin load.
2. Open http://localhost:3000/welcome on your phone (or Chrome device mode) and swipe the three
   slides; tell me what feels off in the design.
3. Try the mic and the live camera once (browser permission prompt).
4. Create the public GitHub repo `akhilsplendid/parklens`, then
   `git remote add origin https://github.com/akhilsplendid/parklens.git && git push -u origin main`.
5. Deploy (docs/DEPLOY.md): Fly for the API, Vercel for the web. ~15 minutes.
6. Then we record (docs/DEMO.md).

## Open items
- Live camera + mic untested end to end on a phone (needs HTTPS tunnel or deploy).
- Nice-to-have if time: end-of-day photo journal; quiz mode; Swedish UI strings.
