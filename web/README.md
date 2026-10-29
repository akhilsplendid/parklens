# ParkLens web

Mobile-first Next.js PWA for ParkLens. Talks to the FastAPI backend in `../api`.

```bash
npm install
cp .env.example .env.local        # point NEXT_PUBLIC_API_URL at the API
npm run dev                       # http://localhost:3000
```

Camera and microphone need a secure context: `localhost` works on the PC; on a phone
use an HTTPS tunnel (`npx cloudflared tunnel --url http://localhost:3000`) or the
"Photo" button, which uses the native camera picker and works over plain HTTP.
