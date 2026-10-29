# Deploying ParkLens for the judges

Goal: one public HTTPS link that works on a phone. Two parts: the API (Fly.io, Stockholm) and
the web app (Vercel). Both free tiers are enough for the judging week.

## 1. API on Fly.io (about 10 minutes)

```powershell
# once
winget install flyctl          # or: iwr https://fly.io/install.ps1 -useb | iex
fly auth signup                # or fly auth login

cd C:\Users\akhil\code\projects\parklens
python scripts\extract_kb.py   # make sure data\generated\kb.json exists (it's copied into the image)
cd api
fly launch --copy-config --no-deploy --name parklens-api --region arn
fly secrets set MODEL_API_KEY=<your key>
fly deploy --dockerfile Dockerfile --build-context ..    # build context is the repo root
fly status                     # note the URL, e.g. https://parklens-api.fly.dev
```

Check: `https://parklens-api.fly.dev/health` should return the park name and 50 animals.

If `fly deploy` complains about the build context, run from the repo root instead:
`fly deploy --config api/fly.toml --dockerfile api/Dockerfile`.

## 2. Web on Vercel (about 5 minutes)

```powershell
cd ..\web
npm i -g vercel
vercel login
vercel --prod
```

When asked for environment variables, set `NEXT_PUBLIC_API_URL` to the Fly URL
(no trailing slash). Or set it in the Vercel dashboard → Project → Settings → Environment
Variables and redeploy. Vercel gives you `https://parklens-<something>.vercel.app`; that is
the link for the submission form and the demo video.

## 3. Lock it down a little

- The API allows every origin (CORS `*`) for the hackathon. After judging, restrict it to the
  Vercel domain in `api/parklens/main.py`.
- Spend limit: set an email alert on the Meta Model API Billing page so a judge hammering the
  demo can't burn the $150 silently. Lens calls are cached per frame and per species.

## 4. Local phone test without deploying

```powershell
# in parklens\web
npx cloudflared tunnel --url http://localhost:3000
# in parklens\api
npx cloudflared tunnel --url http://localhost:8000
```

Put the API tunnel URL in `web\.env.local` as `NEXT_PUBLIC_API_URL`, restart `npm run dev`,
and open the web tunnel URL on the phone. Camera and mic work because the tunnel is HTTPS.
