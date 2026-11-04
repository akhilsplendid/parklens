# Submission text (paste into the hackathon form)

Fill in the two links at the bottom after deploy + push. Keep every claim true to what the demo shows.

## Project name
ParkLens

## One-liner (≤ 140 chars)
A personalized, grounded guide for wildlife parks: tell it who's coming, point it at any animal, and it plans and re-plans your day.

## Description (≈ 250 words)
A day at a wildlife park costs a family around 2,000 SEK, and most of it leaks into queues,
wrong turns, and rides the kids turn out to be too short for. Eye-tracking research finds
that only 10–30% of zoo visitors read the animal signs. ParkLens fixes both halves of that problem for one
real park, Kolmården in Sweden, with a knowledge base built from the park's own website.

You describe your group by voice ("two adults, Mia is five and 110 cm, Leo is nine, we love
big cats, we have five hours"). Muse Voice Transcribe hears it and Muse Spark turns it into a
structured profile. A planner written in plain code ranks the park's 50 animals and 11 rides
by interest, enforces height and age rules, inserts breaks before meltdowns, and orders the
stops by walking distance using GPS points scraped from the park's pages. The model writes
the words of the plan; it never decides whether a child may ride.

At an enclosure you point the phone: SAM 3.1 finds the animal, Muse Spark names it from the
park's species list and tells a child-level or adult-level story using only the park's own
text, with the source link attached. Muse Image then shows the same animal in its wild
habitat or as its prehistoric ancestor, as a before/after slider you can share.

When plans change ("we're tired, one hour left") one sentence re-plans the rest of the day
from where you are standing.

Everything that must be right (height rules, times, sources) is computed; everything that
should be delightful (stories, images) is generated. There is no retrieval step to go wrong:
Spark picks an id from a closed catalogue, code looks up the facts, and anything not on the
list is refused. The pipeline is built for Kolmården's site; another park needs a new
extractor script, nothing else.

## How we used Meta's models
- `muse-voice-transcribe-1.0`: voice onboarding and voice re-planning
- `muse-spark-1.3`: structured-output family profile, species identification (vision),
  grounded narration, plan wording
- `sam-3.1`: finds and boxes the animal in the camera frame (streamed special-token output); the box gates the answer, is drawn on the phone, and is what Muse Image repaints
- `muse-image-1.0`: habitat / ancestor / future "time travel" images from the user's own photo

## Track
Indie developer

## Built during the hackathon?
Yes. All application code was written between Oct 27 and Nov 4, 2026. The park crawl was a
public, robots.txt-permitted crawl made earlier; only the extraction script is in the repo.

## Links
- Repo: https://github.com/akhilsplendid/parklens
- Live demo: <vercel url>
- Video: <youtube url>
