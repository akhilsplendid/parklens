# Submission form answers

Form: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit (login as akhilsplendid).
Every long field is limited to 3,000 characters; the texts below fit. Fill in the two
links at the bottom first (repo must be public; video on YouTube, unlisted is fine).

## Team Name
ParkLens

## Team Members
akhilsplendid (solo)

## Track
Indie Developer Track

## Problem statement
Build for Your World

## Most Viral Track (optional, X post link)
Only if you post the before/after share card + video on X before submitting. Otherwise leave blank.

## Project Description (≤ 3,000 chars)

ParkLens is a personalized, grounded guide for a wildlife park, built for Kolmården in Sweden (the park near my home in Norrköping).

The problem is one every family with small kids knows. A day at the park costs about 2,000 SEK and much of it leaks into queues, wrong turns and rides the kids turn out to be too short for. Eye-tracking research finds that only 10–30% of zoo visitors read the animal signs; small children can't read them at all, and tourists often can't read Swedish.

How it works, in the order a family uses it:

1. Say who's coming. "Two adults, Mia is five and 110 cm, Leo is nine, we love big cats and dolphins, we have five hours." Muse Voice Transcribe hears it and Muse Spark turns it into a structured family profile.

2. Get a day that fits. A planner written in plain code ranks the park's 50 animals and 11 rides by interest, enforces every height and age rule from the park's own pages, inserts a break every 90 minutes, and orders the stops by walking distance using GPS points taken from the park's site. Rides the kids can't ride land in a "Not this time" box with the reason. Muse Spark writes one sentence per stop; it never decides whether a child may ride.

3. Point at an animal. SAM 3.1 finds it in the frame while Muse Spark picks which of the park's listed species it is, or "none". The story is told at the child's level, in the family's language, using only the park's own text, with the source page linked. Anything not on the park's list is refused rather than guessed.

4. Time travel. Muse Image repaints the animal SAM boxed: in its wild habitat, a million years ago as its ancestor, or a century from now. A before/after slider, and a share card for X.

5. Re-plan. "We're tired, one hour left" or "Kids want more rides" re-plans the rest of the day from where the family is standing on the map.

What's computed: eligibility, route, times, sources. What's generated: the words and the pictures. The hackathon rules ban "basic RAG" and "simple image analyzers", and ParkLens is neither: there is no retrieval step, Spark selects from a closed catalogue and code looks up the facts; the Lens combines detection, catalogue identification, grounded narration and image generation around the park's data.

Stack: FastAPI backend (deterministic planner, rules engine, SAM special-token parser, per-IP rate limiting, 28 tests), Next.js 16 PWA (voice, camera, map, share), knowledge base built from a public, robots.txt-permitted crawl of the park's website by one script. All application code was written during the hackathon.

Beyond the hackathon: I want to pitch this to Kolmården's owner, Parks & Resorts, as an embeddable layer on top of their existing site, not a replacement for their app.

## Public GitHub Repository
https://github.com/akhilsplendid/parklens

## 3-Minute Demo Video
<youtube url>

## Describe your use of Meta products (≤ 3,000 chars)

Four models from the Meta Model API, each doing one job in a single flow:

muse-voice-transcribe-1.0 (POST /v1/asr/transcribe). Voice onboarding ("two adults, Mia is five and 110 cm…") and voice re-planning ("we're tired, one hour left"). The web app records with MediaRecorder (webm/opus on Android, mp4 on iOS) and the API forwards the container type.

muse-spark-1.3 (POST /v1/chat/completions, structured output with response_format json_schema). Used four ways: (1) turning the transcript into a Party profile (adults, children with age and height, interests, hours, language, pace); (2) species identification from the camera frame, with the image passed as an image_url and the system prompt holding the park's species catalogue, answering with an id from the list or "none" plus a confidence; (3) narration for a given species and audience, constrained to the park's own text for that animal and asked to write in the family's language; (4) one friendly sentence per stop and a two-sentence summary for the plan, and extraction of re-plan parameters (hours left, pace, prefer rides or animals, done ids) from what the family said. Every one of these returns JSON validated against a pydantic schema; invalid output becomes a 422, never a crash.

sam-3.1 (POST /v1/responses, streamed). The camera frame goes in with the prompt "animal"; the special-token output (<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|>) is parsed with a small regex into boxes. The largest box gates whether there is an animal at all (area ≥ 0.5% of the frame), is drawn on the phone, and is cropped (with padding) as the input to Muse Image, so the time-travel picture is of the animal and not the fence. SAM and the Spark identification run in parallel on the same downscaled frame, so the Lens answers in two round trips.

muse-image-1.0 (POST /v1/images/edits, with the crop as a data URL, reasoning_strength low). Three prompts: wild habitat (the habitat paragraph comes from the park's text when it has one), prehistoric ancestor, and a restored future. Results are labelled "AI-generated artistic impression".

Engineering around the API: one shared httpx AsyncClient, one retry on 429/5xx/transport errors, refusals and non-JSON replies turned into 502/503, camera frames downscaled before upload (saves credits and time), EXIF orientation honoured, narration cached per species/audience/language and pre-warmed in the background as soon as a plan is made so the first look at an animal is instant, and a per-IP rate limit so a week of judging can't drain the credits. Muse Wonder and Muse Code were not used.

## Why are Meta's models important to your solution? (≤ 3,000 chars)

Three reasons, in order of how much they mattered.

First, SAM 3.1's open-vocabulary detection is what makes a camera-first guide possible without training anything. A zoo enclosure is a hard scene: fences, glass, water, a small animal far away. SAM finds "animal" in the frame and gives me a box; that box is what tells the app whether to answer at all, what to draw, and what to send to Muse Image. No other API I had access to does promptable segmentation with this quality at this latency, and I could parse its output with a regex.

Second, Muse Spark's structured output with JSON schema is what lets me keep the model out of the decisions. Every call returns a schema I defined: a Party, a species id from a closed list, a narration pair, a set of re-plan parameters. The planner and the rules engine are plain code; Spark only fills in words and classifications that code then validates. That is the difference between a demo that sometimes says a 110 cm child can ride a 120 cm coaster and one that never does. Spark's vision input at the same endpoint meant species identification and narration could share one client and one prompt style.

Third, having voice, vision, text and image generation behind one OpenAI-compatible API, with one key and $150 of credits, is why a solo developer could build the whole flow in ten days. Muse Voice Transcribe handled Swedish and English with no configuration; Muse Image's edits endpoint turned "repaint this crop as an Ice Age ancestor" into one request. The alternative would have been three or four vendors, each with their own auth, formats and billing.

If this goes further, the open-weight Muse Spark Open model matters too: a park would rather run the narration model inside its own infrastructure than send every visitor's camera frame to a third party, and the grounding approach here (closed catalogue + park text) does not depend on model size.

## Partner technologies feedback (≤ 150 chars)
Did not use Baseten, Modal or Fireworks: the Meta Model API hosted everything this project needed.

## Survey answers (suggestions; your call)
- How likely to build with Meta Model API: Very likely
- Overall opinion: Very favorable
- Recommend Meta Model API (0–5): 4
- Recommend Muse Code (0–5): leave blank or 3 (not used)
- Biggest obstacle: Finding clear documentation or code examples (SAM 3.1's streamed special-token output format had to be reverse-engineered)
- Compared with other models: Somewhat better (structured output + SAM in one API)
- What matters most: Easy integration such as SDKs or an OpenAI-compatible API
- Hardest to switch: Our product is tuned to our current model's behavior and prompts
- What would stop production use: How our data and our users' data would be stored or used (visitors' camera frames)
