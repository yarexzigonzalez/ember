# Deploying

Frontend on **Vercel**, API + Postgres + nightly demo reset on **Render**. Vercel rewrites `/api/*` to Render, so the browser thinks it's all one site. That's what keeps the cookie simple.

```
browser ──> your-app.vercel.app ──(/api/*)──> ember-api.onrender.com ──> Render Postgres
```

Budget about 20 minutes the first time.

## Before you start: free tier stuff

These change, so check [render.com/docs/free](https://render.com/docs/free) and [render.com/pricing](https://render.com/pricing) yourself. As of writing:

- **Free web services sleep after 15 min with no traffic** and take around a minute to wake up. The demo page already shows a "waking up the server" message and retries, so it doesn't look broken. Don't set up a pinger to keep it awake, Render explicitly asks people not to.
- **Free Postgres expires** after a limited window (Render emails you before it happens) and has no backups. Fine for a portfolio demo. Upgrade it if real people are keeping real data in there.
- **Cron jobs aren't free.** They bill per minute with a small monthly minimum (about $1). If you want to stay at $0, skip the Render cron and use the GitHub Actions version at the bottom.
- Vercel's Hobby plan covers the frontend fine.

## 1. Render: API, database, cron

1. Push the repo to GitHub.
2. Render dashboard → **New → Blueprint** → pick the repo. It reads [`render.yaml`](../render.yaml) and sets up:
   - `ember-db`: Postgres
   - `ember-api`: the FastAPI app (runs `alembic upgrade head` on every boot, no-op when there's nothing new)
   - `ember-demo-reset`: the nightly cron
3. It'll ask for `ANTHROPIC_API_KEY`. Paste one in, or leave it blank and Quick Add uses the regex extractor.
4. Wait for the deploy, then check `https://<your-service>.onrender.com/api/health` → `{"status":"ok"}`.
5. Seed the demo once so the button works before the first nightly run: open the **ember-demo-reset** cron job → **Trigger Run**. Or open a shell on `ember-api` and run `python -m scripts.reset_demo`.

### Env vars on the API

All of these come from `render.yaml`. This table is here so you know what they do.

| var | value | why |
|---|---|---|
| `DATABASE_URL` | from `ember-db` | Render gives `postgresql://...`; the app rewrites it to psycopg 3 itself |
| `ENVIRONMENT` | `production` | turns off `/docs`, makes the app refuse to boot without secure cookies |
| `COOKIE_SECURE` | `true` | cookie only rides over https |
| `TRUSTED_PROXY_HOPS` | `2` | Vercel + Render's load balancer. See step 4 to confirm |
| `LOG_CLIENT_IP` | `false` | flip on briefly to check the rate limiter sees real IPs |
| `ANTHROPIC_API_KEY` | yours, optional | Quick Add + follow-up drafts |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | cheap and plenty for field extraction |
| `PYTHON_VERSION` | `3.12.8` | pin it so Render doesn't surprise you |

Leave `CORS_ORIGINS` unset. Everything is same-origin through the rewrite. If something CORS-shaped breaks, the request is probably going to the Render URL directly instead of through `/api`. Fix that, don't add `*`.

## 2. Vercel: frontend

1. Open [`frontend/vercel.json`](../frontend/vercel.json) and swap `ember-api.onrender.com` for your actual Render hostname if it's different. Commit and push.
2. Vercel → **Add New → Project** → import the repo.
3. Set **Root Directory** to `frontend`. It picks up Vite, `npm run build`, and `dist` from `vercel.json`.
4. No env vars needed. The frontend only calls relative `/api/...` paths.
5. Deploy.

The two rewrites in `vercel.json`, in order:

```json
{ "source": "/api/:path*",   "destination": "https://<render>/api/:path*" },
{ "source": "/((?!api/).*)", "destination": "/index.html" }
```

First one is the proxy, second one makes refreshing `/app/pulse` work instead of 404ing.

## 3. Nightly demo reset

The `ember-demo-reset` cron runs `python -m scripts.reset_demo` at 10:00 UTC (2-3am in LA). It deletes the demo user's applications and reseeds ~160 fresh ones spread over the last ~75 days, with a different seed each day so it doesn't look frozen.

### Free alternative: GitHub Actions

Delete the cron block from `render.yaml`, then add the Render database's **External** connection string as a repo secret called `DEMO_DATABASE_URL`, and drop this in `.github/workflows/demo-reset.yml`:

```yaml
name: demo-reset
on:
  schedule: [{ cron: "0 10 * * *" }]
  workflow_dispatch:
jobs:
  reset:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: backend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install .
      - run: python -m scripts.reset_demo
        env: { DATABASE_URL: "${{ secrets.DEMO_DATABASE_URL }}" }
```

GitHub pauses scheduled workflows on repos with no activity for 60 days, so push something now and then.

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
| Logged in, then immediately logged out | cookie not sticking. Check `Secure` is on and you're on https, and that calls go through `/api` on the vercel domain |
| Refreshing a page like `/app/ghost` 404s | the SPA fallback rewrite is missing from `vercel.json` |
| Everyone gets 429'd together | `TRUSTED_PROXY_HOPS` is too low, so the limiter is keying on a proxy IP. Run the IP check above |
| Demo button says "not seeded yet" | run the reset cron once manually |
| Quick Add always says "regex pass" | no `ANTHROPIC_API_KEY`, or the key is bad (check logs for `llm extract fell back`) |
| First request takes ~a minute | free tier waking up, that's normal |
