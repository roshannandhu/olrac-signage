# Deploying to Oracle Cloud Free + Cloudflare + Supabase

A 100-screen deployment on free tiers. `DEPLOYMENT.md` describes the all-in-one Docker
Compose stack with its own Postgres; this is the split-hosting alternative and the two
differ in ways that matter, so follow one or the other rather than mixing them.

| Piece | Runs on | Free-tier limit that binds |
|---|---|---|
| API + worker + Redis | Oracle Cloud VM | CPU, for video transcoding |
| Dashboard | Cloudflare Workers/Pages | none in practice |
| Media | Cloudflare R2 | **10 GB stored** |
| Database | Supabase | **500 MB** |

Operations are a non-issue on R2 (~6.6k writes and ~5k reads a month against limits of
1 M and 10 M). Storage bytes and database bytes are the two things that will actually bite.

---

## 1. The VM

**Take the ARM Ampere shape (4 OCPU / 24 GB), not the 1 GB micro.** The worker runs
`libx264` transcodes; on ⅛ of a core with 1 GB shared between uvicorn, arq, Redis and
ffmpeg it will thrash and be OOM-killed.

Three things must run on it:

1. `uvicorn backend.main:app`
2. the arq worker — or set `RUN_WORKER_IN_PROCESS=true` and let the API host it
3. **Redis** — mandatory, and neither Supabase nor Cloudflare provides it. Self-host it, or
   point `REDIS_URL` at a free managed instance (Upstash works; `rediss://` is accepted, no
   code change). Without Redis: uploads fail outright, nothing is pushed to a screen, and
   every scheduled job stops — including the two that keep the database under 500 MB.

`WORKER_MAX_JOBS` defaults to 2. Raise it only alongside the cores to run it on.

There is **no reverse proxy or TLS in this repo**, and production Android builds require
HTTPS. Put Caddy or a Cloudflare Tunnel in front of the API before provisioning any screen.

## 2. Database (Supabase)

Set `DATABASE_URL` to the **transaction pooler on port 6543**, not 5432. The pool is sized
by `DB_POOL_SIZE` (10) and `DB_MAX_OVERFLOW` (20).

> If `DATABASE_URL` is unset the backend silently falls back to local SQLite on the VM's
> disk and every write is lost on redeploy. `/api/health` reports `"backend": "sqlite"` with
> a warning — check it after the first deploy.

**Retention is not optional at this size.** 100 always-on screens at the 10-second default
item duration write ~864,000 play-log rows a day. Measured on Postgres, that table costs
**387 bytes a row including its nine indexes — about 316 MB a day.**

- `PLAY_LOG_RETENTION_DAYS` — ships at 7. **On the 500 MB free tier with 100 screens, set
  this to 1.** The rollups keep the reporting history; raw rows only need to outlive a
  billing dispute. The prune runs hourly, so the table peaks at roughly retention plus an
  hour.
- `ROLLUP_RETENTION_DAYS` — 400. The aggregated history, ~36k rows/day, pruned at 04:00.
  Nothing pruned this table before; it filled 500 MB on its own in about two months.

Migrations do **not** run automatically except on a first, empty database. After any deploy
that adds one:

```bash
alembic -c backend/alembic.ini upgrade head
```

## 3. Media (R2)

Set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `S3_BUCKET_NAME` / `S3_ENDPOINT_URL`.
Anything with `AWS_ACCESS_KEY_ID=mock` uses local disk instead — which does not survive a VM
rebuild and cannot be shared by a second host.

Two settings decide whether 10 GB is enough:

- **Two renditions, not four** (1080p + 480p). Already the default.
- `DISCARD_SOURCE_AFTER_TRANSCODE=true` — drops the uploaded source once its renditions are
  stored and committed; the 1080p rendition becomes the master. **This cannot be undone:**
  with the source gone, a future codec change means re-uploading rather than re-transcoding.

Together these take a 100 MB upload from ~280 MB in the bucket to ~120 MB, which is the
difference between fifty videos fitting in 10 GB and not.

## 4. Dashboard (Cloudflare)

Built with `@opennextjs/cloudflare`, **not** `@cloudflare/next-on-pages` — the latter
supports Next ≤ 15.5.2 and this app is on 16.

```bash
cd frontend
npm run cf:build     # produces .open-next/worker.js
npm run cf:deploy
```

`NEXT_PUBLIC_API_URL` is **inlined at build time**, so it must be set as a build
environment variable in the Cloudflare project, not a runtime binding.

Add the Pages domain to `CORS_ORIGINS` on the backend — the built-in origin regex only
matches LAN and localhost addresses, so `*.pages.dev` is rejected until you list it.

`frontend/Dockerfile` still expects the old `output: "standalone"` build and no longer
matches this path. It is only relevant if you go back to hosting the dashboard on the VM.

## 5. Before you trust it with 100 screens

```bash
PYTHONIOENCODING=utf-8 backend/venv/Scripts/python.exe -m pytest tests/ -q
```

Then, on the real deployment:

- `GET /api/health` — must report the Supabase host, `"redis": "connected"`, and no warning.
- Watch the Supabase database size for 48 hours with the fleet connected. If it climbs past
  a day's worth, `PLAY_LOG_RETENTION_DAYS` is too high.
- Watch the R2 bucket size across a few content deletions — it must go **down**.
- Confirm screens stay connected past the old 15-socket ceiling. `tests/test_ws_connection_pool.py`
  covers the mechanism; the fleet is the real proof.
