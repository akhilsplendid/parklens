# Status (updated in the night of Oct 28 → 29)

## Done and verified against the real Meta API
- Voice/text onboarding → family profile (structured output)
- Day plan: interest ranking, height/age rules in code, breaks, **GPS routing with walking
  times** from the park's own map links (54 of 61 places located), re-plan from speech
- Lens: SAM 3.1 box + Muse Spark species ID (in parallel) + narration from park text,
  cached per species/audience/language and pre-warmed when a plan is made
- Time travel (wild / ancestor / future) with before/after slider and a share card for X
- Map tab: schematic park map with today's numbered route and "I'm here" demo mode
- 22 backend tests, lint clean; web builds clean
- Docker (api + web), Fly.io config, deploy guide, demo script, README with architecture

## Morning checklist (you)
1. Restart the API (`uvicorn ... --reload` picks up code, but `.env`/KB changes need a restart)
   and open http://localhost:3000/map to see the route on the park map.
2. Try the mic and the live camera once (needs your click on the browser permission prompt).
3. `git init` + first commit, create the public GitHub repo, push. CI runs on push.
4. Deploy (docs/DEPLOY.md): Fly for the API, Vercel for the web. ~15 minutes.
5. Tell me what felt wrong; I'll fix and then we record (docs/DEMO.md).

## Open items
- Dolphin page has no GPS point on the park site, so "Delfin" lands last in the route. Could
  pin it by hand next to Delfinexpressen (same area).
- Live camera + mic untested end to end on a phone (needs HTTPS tunnel or deploy).
- `parklens:clock` localStorage override exists for the re-plan shot; a small UI toggle would be nicer.
- Nice-to-have if time: end-of-day photo journal; quiz mode; Swedish UI strings.
