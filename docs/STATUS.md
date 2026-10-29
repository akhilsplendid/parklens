# Status (Oct 29, afternoon)

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
