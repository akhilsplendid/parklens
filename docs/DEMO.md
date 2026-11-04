# ParkLens: 3-minute demo video script

Record on a phone (portrait) with screen recording, plus one laptop clip for the architecture.
Speak slowly; judges watch dozens of these. Every claim below is something the app really does.

## Shot list

| Time | Screen | Say |
|---|---|---|
| 0:00–0:20 | A photo of a park gate, then the ParkLens home screen | "A day at a wildlife park costs a family 2,000 kronor and most of it goes to queues, wrong turns and rides the kids are too short for. And research says only one visitor in five reads the animal signs. ParkLens fixes both." |
| 0:20–0:45 | Family tab. Hold the mic: *"Two adults, Mia is five and 110 centimetres, Leo is nine and 135. We love big cats and dolphins, we have five hours."* The group card appears. | "You just tell it who's coming. Meta's Voice Transcribe hears it, Muse Spark turns it into a profile." |
| 0:45–1:15 | Tap *Plan our day*. Scroll the plan. Point at the **Not this time** box. | "Here's the day: cats and dolphins first, breaks every ninety minutes, and Wildfire is skipped because Mia is 10 centimetres too short. That rule is checked in code, not by the model, so it can't hallucinate a yes." |
| 1:15–1:30 | Map tab. The route numbered on the park's own GPS points. | "The route comes from the GPS points on the park's own pages, ordered by walking distance for a five-year-old's legs." |
| 1:30–2:00 | Lens tab. First point it at something that is not a park animal (a dog, a mug): "not one of Kolmården's listed species". Then the tiger clip. Green box, narration plays aloud for Mia, source link. | "Point at an animal. SAM 3.1 finds it, Muse Spark names it from the park's species list, and it refuses anything that isn't on the list. Then it tells Mia's version of the story, using only the park's own text, with the source right there. No retrieval, no guessing: a closed catalogue and a lookup." |
| 2:00–2:20 | Tap *1 million years ago*. Drag the slider. Tap *Share*. | "Then the fun part. Muse Image repaints what SAM boxed: the same tiger a million years ago. Kids love it, and parents share it." |
| 2:20–2:40 | Plan tab. Tap *We're tired, one hour left*. New short plan appears and is read aloud. | "Three o'clock, everyone's tired. One sentence, and the rest of the day is re-planned from where you're standing." |
| 2:40–2:55 | Laptop: the architecture diagram from the README. | "Four Meta models, one FastAPI backend, a Next.js PWA. What has to be right is computed: height rules, routing, the time budget, sources. What should be delightful is generated: the words and the pictures. The knowledge base is built from the park's website by one script." |
| 2:55–3:00 | ParkLens logo, the public URL, the GitHub link. | "ParkLens. Built for Kolmården; swap the extractor and it works for your park." |

## Generated clips (Higgsfield, no branding, free to use in the video)

Download these from your browser (our tooling can't reach the CDN) into `docs/assets/`
(gitignored) before editing:

- Opening shot, 6 s, 9:16, with ambience: family walking into a pine-forest park at golden hour
  https://d8j0ntlcm91z4.cloudfront.net/user_35mXGTcXdv7Rpzl6WFcHzKJVf0G/hf_20261029_122346_2e9cdda2-6035-4a5d-a65d-b711fd2fd770.mp4
- Tiger clip, 8 s, 16:9: play it full-screen on the laptop and point the phone's Lens at it
  https://d8j0ntlcm91z4.cloudfront.net/user_35mXGTcXdv7Rpzl6WFcHzKJVf0G/hf_20261029_123211_9d6935c5-4165-4df5-bee6-1467b1ccf3ae.mp4

Both are also in your Higgsfield library.

## Before recording

- [ ] Public URL deployed (docs/DEPLOY.md) and tested on the phone
- [ ] Family set up in advance? No: do it live, it's the voice moment. But rehearse the sentence.
- [ ] Plan warm-up: make the plan once before recording so narration is cached and the Lens answers fast
- [ ] Tiger clip (above) ready full-screen on the laptop; don't use the park's own images
- [ ] Phone on Do Not Disturb, brightness up, battery > 50%
- [ ] For the re-plan shot, tap the small clock line under the re-plan box on the Plan tab until it says 15:00 (demo clock); tap again to go back to real time

## Sources for the spoken claims

- Sign reading: 10–30% of zoo visitors read animal signs (Spooner, Heath & Dymond 2024, https://www.mdpi.com/2673-5636/5/3/29)
- LLM planners and hard constraints: GPT-4 met every constraint in 0.6% of plans (Xie et al., TravelPlanner, ICML 2024, https://arxiv.org/abs/2402.01622)
- 2,000 SEK: two adult + two child day tickets plus food at Kolmården, 2026 prices; say "about"

## Judging rubric, mapped

- **Impact (30%)**: shots 1 and 3 (the problem and the height rule)
- **Use of Meta tooling (25%)**: shots 2, 5, 6, 8 (five models named on screen)
- **Technical depth (20%)**: shot 3 ("checked in code") and shot 8 (architecture)
- **Demo (25%)**: shots 5 and 6 (Lens and time travel)
- Bonus **Best Creative Build**: shot 6. Bonus **Most Viral**: post the share card on X with the video.
