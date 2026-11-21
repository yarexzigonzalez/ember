# Deploying

All free, nothing behind a paywall:

- **Neon**: Postgres (free tier, doesn't expire)
- **Render**: the FastAPI app (free web service)
- **Vercel**: the React app (Hobby plan), and it proxies `/api/*` to Render so the browser only sees one site
- **GitHub Actions**: resets the demo account every night

```
browser ──> your-app.vercel.app ──(/api/*)──> your-api.onrender.com ──> Neon Postgres
```

Free tier tradeoff: Render free services sleep after 15 min with no traffic and take about a minute to wake up. The demo page shows a "waking up the server" note and retries, so it doesn't look broken.

## 1. Neon: the database

1. Sign up at [neon.tech](https://neon.tech) and create a project (any name, Postgres 16, region close to Render's Oregon/Ohio).
2. Dashboard → **Connect** → copy the connection string. Looks like `postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require`.

The app rewrites `postgresql://` to the psycopg 3 driver itself, so paste it as-is. Tables get created on the API's first boot.

## 2. Render: the API

1. Render dashboard → **New → Blueprint** → pick this repo. It reads [`render.yaml`](../render.yaml) and makes one free web service.
2. It asks for two values:
   - `DATABASE_URL`: the Neon string
   - `ANTHROPIC_API_KEY`: optional, leave blank and Quick Add uses the regex extractor
3. Wait for the deploy, then grab the service URL from the top of the page (like `https://ember-api-abcd.onrender.com`).
4. Open `<that url>/api/health` → should say `{"status":"ok"}`.

## 3. Vercel: the frontend

1. Put your Render URL into [`frontend/vercel.json`](../frontend/vercel.json), in the `/api/:path*` destination. Commit + push.
2. Vercel → **Add New → Project** → import the repo → **Root Directory: `frontend`** → Deploy. No env vars.

Vercel redeploys on every push to `main`.

## 4. Demo account

1. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**. Name: `DATABASE_URL`, value: the Neon string.
2. **Actions** tab → **demo-reset** → **Run workflow**. That seeds the demo right now.

After that it runs every night at 10:00 UTC. GitHub pauses scheduled workflows after 60 days with no repo activity, so push something now and then (or hit Run workflow).

### Env vars on the API

| var | value | why |
|---|---|---|
| `DATABASE_URL` | Neon string | the app switches it to psycopg 3 itself |
| `ENVIRONMENT` | `production` | turns off `/docs`, refuses to boot without secure cookies |
| `COOKIE_SECURE` | `true` | cookie only rides over https |
| `TRUSTED_PROXY_HOPS` | `2` | Vercel + Render's load balancer, see the IP check below |
| `LOG_CLIENT_IP` | `false` | flip on briefly to check the rate limiter sees real IPs |
| `ANTHROPIC_API_KEY` | optional | Quick Add + follow-up drafts |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | cheap and plenty for field extraction |
| `PYTHON_VERSION` | `3.12.8` | pinned so Render doesn't surprise you |

Leave `CORS_ORIGINS` unset. Everything is same-origin through the rewrite. If something CORS-shaped breaks, a request is going to the Render URL directly instead of through `/api`. Fix that, don't add `*`.

## 4. Post-deploy checks

Do these on the real Vercel URL, not localhost.

### Cookies

1. Sign up, then open DevTools → Application → Cookies → your vercel domain.
2. `ember_session` should be **HttpOnly ✓, Secure ✓, SameSite Lax, Path /**, and the Domain should be your vercel host (no leading dot, because we never set one).
3. Refresh. You should still be logged in. Log out, and the cookie should be gone and `/app` should bounce you to login.
4. Network tab: every API call should go to `your-app.vercel.app/api/...`. If you see `onrender.com` in there, something's calling the backend directly.

### Rate limiter sees real IPs

1. Render → `ember-api` → Environment → set `LOG_CLIENT_IP=true`, save (it redeploys).
2. Try logging in with a wrong password once.
3. Render logs should show something like:
   ```
   client ip: peer=10.x.x.x xff='203.0.113.9, 76.76.x.x' hops=2 -> 203.0.113.9
   ```
   The `->` value should be **your** public IP (google "what is my ip"). If it's a Vercel/Render-looking address instead, count the entries in `xff`: your IP's position from the right is the number `TRUSTED_PROXY_HOPS` should be.
4. From your phone on cellular (different IP), a wrong login should not be blocked by attempts you made on wifi.
5. Hit wrong passwords 10 times in a row → the 11th gets a 429.
6. Set `LOG_CLIENT_IP=false` again. No reason to keep IPs in logs.

Heads up: someone who finds the raw Render URL can skip Vercel and type their own `X-Forwarded-For`. The limiter is there to slow down casual brute forcing, not to be a firewall.

### Timezone

1. Sign up in a normal browser. Settings should already show your local timezone (it comes from the browser at signup).
2. Add a job straight into **Applied** late at night. Its "Applied" date should be *your* date, not tomorrow's UTC date.
3. Change the timezone to something far away (`Asia/Tokyo` or `Pacific/Kiritimati`) and save. The sprint ring's date range should jump to that zone's Monday-Sunday.
4. The demo account should show `America/Los_Angeles` and refuse to change it.

### Demo

1. Open the site in a private window → **View live demo**. If Render was asleep you'll see the "waking up the server" note for up to a minute, then you're in.
2. Board, Market Pulse, Ghost Radar, and the sprint ring should all have data.
3. Settings → Save should be disabled with a "locked" note.

## When things break

| symptom | likely cause |
|---|---|
| API won't boot, logs say `COOKIE_SECURE has to be true` | that's on purpose, set `COOKIE_SECURE=true` |
| Signup/login does nothing or errors | `vercel.json` isn't pointing at *your* Render URL, or the API is still asleep/deploying |
| Logged in, then immediately logged out | cookie not sticking. Check `Secure` is on and you're on https, and that calls go through `/api` on the vercel domain |
| Refreshing a page like `/app/ghost` 404s | the SPA fallback rewrite is missing from `vercel.json` |
| Everyone gets 429'd together | `TRUSTED_PROXY_HOPS` is too low, so the limiter is keying on a proxy IP. Run the IP check above |
| Demo button says "not seeded yet" | run the demo-reset workflow once (Actions tab) |
| Quick Add always says "regex pass" | no `ANTHROPIC_API_KEY`, or the key is bad (check logs for `llm extract fell back`) |
| First request takes ~a minute | free tier waking up, that's normal |
