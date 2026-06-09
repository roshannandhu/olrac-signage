# Olrac Signage — Build Plan & Detailed Prompt Playbook

> **Purpose.** This is the complete build manual for Olrac Signage (an AbleSign-style cloud digital-signage platform). It contains **long, self-contained, copy-paste prompts** that route work to the right tool:
> - **Frontend → Claude Code** (the admin dashboard + the TV-player kiosk).
> - **Backend → opencode** with free models (**DeepSeek V4 Flash**, **Big Pickle**, **MiMo V2.5**, **Nemotron 3 Ultra**) and **Gemini Pro** for the architecture-critical parts.
>
> The two reference designs (`admin.html`, `tv-player.html`) are already converted into working React + Vite + TypeScript apps in `admin/` and `tv/`. Those apps are the **visual + behavioural source of truth** — the prompts below tell each model exactly how to reproduce or extend them and how to wire them to the backend.
>
> **How to read a prompt.** Every prompt has the same anatomy: **ROLE → CONTEXT → FILES → SPEC (endpoint-by-endpoint or component-by-component) → EXAMPLES → EDGE CASES → ACCEPTANCE → OUTPUT RULES.** Paste the whole thing. Do not summarise it.

---

## 0. Locked architecture decisions

| Area | Decision | Notes |
|------|----------|-------|
| Admin app | React 18 + Vite + TS (port **5173**) | Built with **Claude Code**. Exists in `admin/`. |
| TV player | React 18 + Vite + TS **web kiosk** (port **5174**) **+ optional native Android-TV WebView kiosk wrapper** (T5) | Built with **Claude Code**. Web app in `tv/`. The Kotlin wrapper loads the deployed URL fullscreen, auto-starts on boot, and kiosk-locks — for real Android TV / Fire TV. |
| Backend API | **Python 3.11 + FastAPI** | Built with **opencode** free models + **Gemini Pro**. |
| DB / Auth / Storage | **Supabase** (Postgres + Supabase Auth + Storage bucket `media`) | Removes a lot of boilerplate the free models would otherwise generate. |
| Real-time | **Polling** | TV heartbeats every 30 s; TV polls its playlist every 30 s. No WebSockets in v1. |
| Security | **Two tokens** | Admin = Supabase Auth JWT (verified by FastAPI). Screen = long-lived FastAPI-issued opaque token (read-only + heartbeat + playback-log only). |

---

## 0.5 Reference notes — what we borrow vs. deliberately skip

Two mature open-source projects were evaluated as references. **No source code is pulled from either** (license + stack + size). We borrow only ideas:

- **`litrik/displayer`** — Android TV signage player (Kotlin + Jetpack Compose, renders JSON content **natively, no WebView**, with a Ktor admin server). **Borrow: its deployment model only** — run as an Android-TV *launcher*, **auto-start after reboot** (by disabling the stock launcher), fullscreen unattended loop. We realise this as the **T5 native WebView kiosk wrapper** around our existing React TV app. **Skip:** its Compose JSON renderer, Ktor admin server, weather/multi-region layout — our React TV app + FastAPI already cover those.
- **Xibo** — mature CMS (**PHP CMS + per-platform native players**, Windows .NET / Linux / commercial Android-webOS-Tizen, **AGPL-3.0**, self-hosted/cloud). **Pull no code:** AGPL would force our entire stack to AGPL, and it's a different stack ("large, hard to customize"). It mainly **validates** what we already build — proof-of-play analytics (B6), screen groups / multi-display (B5), cloud + offline caching (T3).
- **Deferred to a post-v1 roadmap** (NOT built by these prompts unless you ask): **(1) Scheduling / dayparting** — real time-of-day + day-of-week windows behind the admin's "⏰ Hours" stub (add a `schedules` table + make `resolve_playlist_for_screen` schedule-aware; `content.start_date/expiry_date` already exist). **(2) User management / roles / workspaces** — multi-tenant (v1 is single-admin). **(3) Multi-region layouts** — v1 is single-zone fullscreen.

---

## 1. How the system actually works (the loop you are building)

Read this once. It lets you judge whether any generated code is *correct*, not merely whether it compiles.

```
┌─ ADMIN (writes) ─────────────┐         ┌─ BACKEND (FastAPI + Supabase) ─┐         ┌─ TV (reads + reports) ─┐
│ 1. Upload media              │  POST   │ stream file → Supabase Storage │         │                        │
│                              │ ───────▶│ insert row in `content`        │         │                        │
│ 2. Enter pairing code +      │  POST   │ link pending screen → account, │  GET    │ 0. request 6-digit code│
│    pick orientation          │ ───────▶│ set name + orientation + owner │◀─────── │    on first launch     │
│ 3. Build playlist (ordered)  │  PUT    │ replace playlist items (txn)   │         │ 4. poll /screens/me    │
│                              │ ───────▶│                                │ ───────▶│    every 30s → resolve │
│                              │         │ resolve_playlist_for_screen()  │         │    playlist, cache,    │
│                              │         │   (group overrides individual) │         │    play, rotate        │
│ 6. View Proof-of-Play report │  GET    │ aggregate `playback_logs`      │◀─────── │ 5. heartbeat 30s        │
│                              │ ◀───────│                                │◀─────── │ 6. POST playback logs  │
└──────────────────────────────┘         └────────────────────────────────┘         └────────────────────────┘
```

**The two frontends never talk to each other — only to the backend. Admin writes; TV reads + reports.** Every authorization rule, every endpoint, exists to serve one of those six steps.

---

## 2. Design system (strict — both frontends already follow it)

```
Fonts        'Outfit' (all UI text) · 'JetBrains Mono' (pairing codes, durations, clock, timestamps)
Accent       #1E293B (deep slate)  ── absolutely NO purple anywhere
Admin theme  bg #F9FAFB · surfaces #fff · borders #E5E7EB / #D1D5DB · text #111827 / #6B7280 / #9CA3AF
TV theme     bg #0F172A · glass rgba(255,255,255,0.04) · text rgba(255,255,255,.9/.55/.25)
Status       green #10B981 · amber #F59E0B · red #EF4444 · blue #3B82F6
Slate chips  bg #F1F5F9 · text #334155
Radius       14px cards · 9px controls (admin) · 12–24px glass (TV)
Shadows      --sh 0 1px 6px rgba(0,0,0,.06) · --sh-lg 0 4px 22px rgba(0,0,0,.10)
Feel         clean, minimal, generous whitespace, soft 0.18–0.22s fade/translate transitions
```

The full token set lives as CSS variables in `admin/src/styles.css` (`:root{ --accent … }`) and `tv/src/styles.css`. **Reuse those tokens verbatim** — never introduce new colours.

**Orientation rule** (used in the pairing wizard, screen settings, and TV rotation):
`Landscape = 0° · Portrait = 90° · Upside Down = 180° · Reverse Portrait = 270°`. Stored as the enum `D0 | D90 | D180 | D270`.

---

## 3. Data model (the shared contract — referenced by every prompt)

```
profiles        id (uuid = auth.users.id) · email (text) · name (text) · role (text default 'admin') · created_at
content         id (uuid) · owner_id (uuid → profiles) · name (text) · type ('video'|'image')
                · orientation ('landscape'|'portrait') · storage_path (text) · public_url (text)
                · duration_seconds (int default 0) · file_size (bigint) · tags (text[] default '{}')
                · start_date (timestamptz null) · expiry_date (timestamptz null) · created_at
screens         id (uuid) · owner_id (uuid → profiles, NULLABLE while pending) · name (text)
                · description (text null) · pairing_code (text null) · pairing_code_expires_at (timestamptz null)
                · orientation ('D0'|'D90'|'D180'|'D270' default 'D0') · status ('pending'|'online'|'offline')
                · last_seen_at (timestamptz null) · screen_token (text unique) · tags (text[]) · created_at
playlists       id (uuid) · screen_id (uuid → screens, UNIQUE, null) · group_id (uuid → screen_groups, UNIQUE, null)
                · updated_at                          -- a playlist belongs to EXACTLY ONE of screen / group
playlist_items  id (uuid) · playlist_id (uuid → playlists) · content_id (uuid → content)
                · position (int) · duration_override (int null)
screen_groups   id (uuid) · owner_id (uuid → profiles) · name (text) · created_at
group_screens   group_id (uuid → screen_groups) · screen_id (uuid → screens)   -- composite PK (m:n)
websites        id (uuid) · owner_id (uuid → profiles) · name (text) · url (text) · created_at
playback_logs   id (uuid) · screen_id (uuid → screens) · content_id (uuid → content)
                · played_at (timestamptz) · duration_played (int seconds)
```

**Playlist resolution (the one tricky rule):** a screen's *effective* playlist = the playlist of the group it belongs to **if that group has a playlist with items**, otherwise the screen's own playlist. Implemented once as `resolve_playlist_for_screen(session, screen_id)` and consumed by `GET /screens/me`.

---

## 4. API contract (the exact surface both frontends consume)

> Admin routes require `Authorization: Bearer <supabase_access_token>`. Screen routes require `Authorization: Bearer <screen_token>`.
> **Every** response is `{"data": <result>, "error": null}` on success or `{"data": null, "error": {"message": "...", "code": "..."}}` on failure (HTTP status set appropriately). Implement with one helper + one global exception handler.

```
AUTH
  POST   /auth/register   {email,password,name}                         → profile                   public
  POST   /auth/login      {email,password}                              → {access_token,refresh_token,user}  public
  GET    /auth/me                                                       → profile                   admin

CONTENT
  GET    /content?type=&orientation=&sort=&search=&tags=                → Content[]                 admin
  POST   /content/upload  multipart(file, name?, tags?)                 → Content                  admin
  PATCH  /content/{id}    {name?,tags?,start_date?,expiry_date?}        → Content                  admin
  DELETE /content/{id}                                                  → {ok:true}                admin

SCREENS / PAIRING
  POST   /screens/request-code                                         → {code,screen_token}      public (TV)
  GET    /screens/me                                                   → {screen, playlist}       screen
  POST   /screens/pair    {code,name,orientation}                      → Screen                   admin
  GET    /screens                                                      → Screen[]                 admin
  PATCH  /screens/{id}    {name?,description?,orientation?,tags?}       → Screen                   admin
  POST   /screens/{id}/heartbeat                                       → {ok:true}                screen
  DELETE /screens/{id}                                                 → {ok:true}                admin

PLAYLISTS
  GET    /screens/{id}/playlist                                        → PlaylistItem[]+content   admin
  PUT    /screens/{id}/playlist  {items:[{content_id,position,duration_override?}]}  → items[]     admin

GROUPS
  GET    /groups                                                       → Group[]+screens          admin
  POST   /groups          {name,screen_ids[]}                          → Group                    admin
  PATCH  /groups/{id}     {name?,screen_ids?}                          → Group                    admin
  PUT    /groups/{id}/playlist   {items:[...]}                         → items[]                  admin
  DELETE /groups/{id}                                                  → {ok:true}                admin

REPORTING
  POST   /playback/log    [{content_id,played_at,duration_played}]     → {ok:true,inserted:n}     screen
  GET    /reports/summary?from=&to=                                    → per-content totals       admin
  GET    /reports/by-screen?from=&to=                                  → per-screen totals        admin
  GET    /reports/hourly?from=&to=                                     → per-hour buckets         admin
  GET    /reports/export?type=summary|by-screen|hourly&from=&to=       → text/csv download        admin

WEBSITES
  GET    /websites                                                     → Website[]                admin
  POST   /websites        {name,url}                                   → Website                  admin
  DELETE /websites/{id}                                                → {ok:true}                admin
```

---

## 5. Model routing (which model gets which backend prompt)

| Model | Backend prompts | Why |
|-------|-----------------|-----|
| 🟣 **Gemini Pro** | **B1** (scaffold + schema), **B2** (auth + two-token), **B4** (pairing flow), **B5** (playlists + group resolution) | These cascade — a wrong schema, a wrong token rule, or a wrong pairing handshake breaks everything downstream. Spend the strong model here. |
| 🔵 **DeepSeek V4 Flash** | **B3** (content + storage), **B6** (reports + CSV) | Strong general coder; reliable on well-specified CRUD + SQL aggregation. |
| 🟢 **Nemotron 3 Ultra** | the boilerplate inside **B1** / **B7** (Pydantic models, config, project files) | Big context window, good at mechanical multi-file boilerplate. |
| 🟡 **MiMo V2.5** | **B7** (websites + wiring + smoke test) | Fine for small, isolated, low-risk routes and glue. |
| 🟠 **Big Pickle** | repetitive serializers / response models if you split a prompt | Identity uncertain — treat as a general free coder; reassign if quality is poor. |

**Rule of thumb:** schema, auth boundary, pairing handshake, playlist resolution → **Gemini Pro**. Plain CRUD, serializers, glue → free models. All **frontend** work → **Claude Code** (it reads the existing `admin/` & `tv/` code and the reference HTML directly).

### Hard rules for the free models (paste these into every opencode session, every time)
1. **Re-paste the Context Block (§6).** Free models have no memory across chats.
2. **One prompt = one file group.** Never "build the whole API".
3. **Complete files only.** End every prompt with: *"Output every file in full, top to bottom. No `...`, no `# unchanged`, no ellipses, no 'rest of file stays the same'. If a file is long, still print all of it."*
4. **Do not invent.** *"Use exactly the field names, routes, enums and response shape given. Do not add, rename, or remove fields or endpoints."*
5. **Explain before coding** (Gemini-tier prompts): *"First, in 3–5 lines, restate the data flow and the tricky rule. Then write the code."* — strong models catch their own mistakes when they reason first.
6. **On error:** paste the traceback + the offending file and say *"Fix only this. Return the full corrected file and nothing else."*
7. **Supabase gotchas are real — honour every "⚠️ KNOWN PITFALLS" block.** The three that bite at runtime: verify admin JWTs via **`supabase.auth.get_user(token)`** (works with Supabase's new asymmetric signing keys; a hardcoded HS256 decode does not), don't run asyncpg through the **transaction pooler** (use the direct/session connection, or disable the statement cache), and make sure the **public `media` Storage bucket exists** before uploads.

---

## 6. The Context Block (paste at the TOP of every backend/opencode session)

```
PROJECT: Olrac Signage backend — a cloud digital-signage REST API.
STACK:   Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async · asyncpg.
         Database/Auth/Storage = Supabase. Postgres accessed directly via DATABASE_URL.
         Supabase Auth (GoTrue) for ADMIN login. Supabase Storage bucket "media" for uploaded files.
SERVER:  uvicorn. Settings via pydantic-settings reading a .env file.
ENV:     SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET,
         DATABASE_URL, SCREEN_TOKEN_SECRET, CORS_ORIGINS="http://localhost:5173,http://localhost:5174"

TWO-TOKEN SECURITY (non-negotiable):
  • ADMIN requests carry a Supabase Auth JWT in `Authorization: Bearer ...`.
    Dependency `require_admin` verifies it — DEFAULT: supabase.auth.get_user(token) (works with Supabase's
    new asymmetric signing keys; HS256-with-SUPABASE_JWT_SECRET only works on legacy projects) — then loads
    the matching `profiles` row and returns it. 401 if missing/invalid.
  • SCREEN requests carry a long-lived opaque `screen_token` we issued at request-code time.
    Dependency `require_screen` looks it up in `screens.screen_token` and returns that screen row.
    A screen may ONLY: read its own data (/screens/me), heartbeat, and POST playback logs. Nothing else.

RESPONSE ENVELOPE (every endpoint, success and error):
  success → {"data": <payload>, "error": null}
  failure → {"data": null, "error": {"message": "<human text>", "code": "<machine code>"}}
  Implement helpers ok(data) / fail(message, code, status) and a global exception handler
  that wraps ANY unhandled error in this shape (never leak a raw stack trace to the client).

DATA MODEL: [paste §3 verbatim]
ORIENTATION ENUM: D0,D90,D180,D270.  CONTENT TYPE: video|image.  CONTENT ORIENTATION: landscape|portrait.
SCREEN STATUS: pending|online|offline.

GLOBAL RULES: full Python type hints; Pydantic models for every request/response body; validate all inputs
with Pydantic/Zod-style constraints; scope every admin query to the caller's owner_id; never trust the client.
Output complete files only — no placeholders, no ellipses. Explain any non-obvious decision in ONE line.
```

---

## 7. Build order

```
PHASE 1  Backend (opencode)        B1 → B2 → B3 → B4 → B5 → B6 → B7      (smoke test must pass before Phase 4)
PHASE 2  Admin app (Claude Code)   A1 → A2 → A3 → A4 → A5 → A6 → A7      (already built in admin/; prompts = spec/regen)
PHASE 3  TV player (Claude Code)   T1 → T2 → T3 → T4 (+ T5 optional)     (web app built in tv/; T5 = native Android-TV kiosk shell)
PHASE 4  Integrate + deploy        I1 → I2
```

Build the backend first — it is the contract. The admin app's A1–A3 can be developed in parallel against the documented contract (§4) using the mock layer that already exists in `admin/src/store.ts`. **Test after every prompt.** Never start the next phase until the current one runs end-to-end.

> The frontend already exists. The Phase-2/3 prompts are written as **complete regeneration specs**: feed them to Claude Code to rebuild from scratch, to extend a page, or to wire a mock page to the real API. Each names the exact files that exist in `admin/` and `tv/` today.

---
---

# PHASE 1 — BACKEND PROMPTS (opencode)

> Run each in a fresh opencode session with the model named in its header. **Paste the Context Block (§6) first, then the prompt.**

---

## B1 — Project scaffold + Supabase schema  🟣 Gemini Pro

```
[PASTE CONTEXT BLOCK §6]

ROLE: Senior Python backend engineer. You are bootstrapping the Olrac Signage FastAPI service and its
Supabase Postgres schema. This is the foundation every other prompt builds on — be exact.

FIRST (before code): in 4 lines, restate (a) the two-token security model, (b) the response envelope,
(c) the screen↔playlist↔group relationship, (d) why playlists.screen_id and playlists.group_id are both
nullable + unique.

FILES TO CREATE (print each one fully):
  app/__init__.py
  app/main.py            FastAPI() app; CORS from CORS_ORIGINS; include EVERY router (auth, content,
                         screens, playlists, groups, playback, reports, websites — import-guard the ones
                         not built yet with try/except ImportError so the app still boots);
                         register_exception_handlers(app); GET /health → ok({"status":"ok"}).
                         On startup, launch the offline-sweeper background task (defined in B4; import-guard).
  app/config.py          class Settings(BaseSettings) with every ENV var from the Context Block, typed;
                         cors_origins parsed into a list[str]; a single `settings = Settings()` instance.
  app/db.py              async SQLAlchemy 2.0 engine from DATABASE_URL (asyncpg); async_sessionmaker;
                         `async def get_session()` FastAPI dependency yielding an AsyncSession.
  app/supabase_client.py supabase-py client built with SUPABASE_URL + SUPABASE_SERVICE_KEY (service role,
                         for Storage + Auth admin). Expose `supabase`.
  app/responses.py       ok(data) -> dict; fail(message, code="error", status=400) -> JSONResponse;
                         class ApiError(Exception) carrying message/code/status;
                         register_exception_handlers(app) mapping ApiError + RequestValidationError +
                         generic Exception into the envelope. NEVER leak a raw traceback.
  app/models.py          SQLAlchemy ORM classes for EVERY entity in the data model, exact column names,
                         types, FKs, nullability, defaults, the unique constraints, and relationships
                         (Screen 1:1 Playlist; Playlist 1:N PlaylistItem; ScreenGroup N:M Screen via
                         group_screens; PlaylistItem N:1 Content).
  app/schemas.py         Pydantic v2 models: for each entity a Read model; plus the request bodies named
                         in §4 (RegisterIn, LoginIn, ContentPatchIn, PairIn, ScreenPatchIn, PlaylistPutIn,
                         GroupCreateIn, GroupPatchIn, WebsiteCreateIn, PlaybackLogIn). Use Literal[...] for
                         the enums. ConfigDict(from_attributes=True) on Read models.
  app/routers/__init__.py (empty)
  requirements.txt       fastapi, uvicorn[standard], sqlalchemy>=2, asyncpg, pydantic>=2, pydantic-settings,
                         python-jose[cryptography], supabase, python-multipart, httpx
  .env.example           every ENV var with placeholder values + a comment on where to find each in Supabase
  README.md              setup + run steps (venv, install, run schema.sql, uvicorn)

  supabase/schema.sql    ONE idempotent SQL migration for the Supabase SQL editor:
                         - enable pgcrypto (gen_random_uuid()).
                         - create enum types OR use CHECK constraints for content.type, content.orientation,
                           screens.orientation (D0/D90/D180/D270), screens.status.
                         - create ALL tables from the data model with uuid PKs default gen_random_uuid(),
                           FKs with ON DELETE CASCADE where a child cannot outlive its parent
                           (playlist_items→playlists, group_screens→both, playlists→screen/group).
                         - UNIQUE on playlists.screen_id, playlists.group_id, screens.screen_token;
                           composite PK on group_screens(group_id, screen_id).
                         - indexes on every FK + screens.pairing_code + screens.screen_token + content.owner_id
                           + playback_logs.(screen_id, played_at).
                         - LEAVE RLS DISABLED (the service key bypasses it; we authorize in FastAPI).

EXACT COMMANDS to print at the end:
  python -m venv .venv && .venv\Scripts\activate (Windows) ;  pip install -r requirements.txt
  # paste supabase/schema.sql into Supabase → SQL Editor → Run
  uvicorn app.main:app --reload --port 8000

⚠️ KNOWN PITFALLS (handle these or it breaks on real Supabase — do NOT skip):
  • DATABASE_URL must be the DIRECT connection or the SESSION pooler (host ...supabase.co / port 5432). If you
    use the TRANSACTION pooler (port 6543, pgbouncer), asyncpg PREPARED STATEMENTS fail at runtime — in that
    case build the engine with create_async_engine(url, connect_args={"statement_cache_size":0,
    "prepared_statement_cache_size":0}). Supabase requires SSL (asyncpg: connect_args ssl, or "?sslmode=require").
  • In app/db.py, convert a "postgres://"/"postgresql://" URL to the async driver "postgresql+asyncpg://".
  • A PUBLIC-READ Storage bucket named "media" must exist (Supabase → Storage → New bucket → Public). B3 uploads
    there and the TV reads public_url. Add "create the media bucket" as a step in README.md.
  • Keep `create extension if not exists pgcrypto;` at the top of schema.sql so gen_random_uuid() is available.

ACCEPTANCE: `uvicorn app.main:app` boots with zero errors and GET /health returns
{"data":{"status":"ok"},"error":null}. The schema runs clean on a fresh Supabase project.

OUTPUT RULES: print every file in full, no ellipses. After the files, give the 3-line schema-relationship
explanation. Do not write any endpoint logic yet beyond /health.
```

---

## B2 — Authentication (Supabase Auth proxy + two-token deps)  🟣 Gemini Pro

```
[PASTE CONTEXT BLOCK §6]

ROLE: Backend security engineer. Implement admin auth (proxied to Supabase Auth) and the two FastAPI
dependencies that guard every route. Getting the token boundary wrong is a security bug — be precise.

FIRST (before code): in 3 lines explain why screens are NOT Supabase users and instead authenticate with
an opaque token row, and what a screen is forbidden from doing.

FILES TO CREATE / EDIT (print fully):
  app/security.py
     • generate_screen_token() -> str  : secrets.token_urlsafe(32). Opaque, unguessable.
     • generate_pairing_code() -> str  : a 6-digit numeric string (zero-padded). (B4 ensures uniqueness.)
  app/deps.py
     • async def require_admin(authorization: str = Header(None), session = Depends(get_session)) -> Profile:
         - extract the Bearer token; if absent → raise ApiError("Not authenticated","unauthenticated",401).
         - VERIFY the token (see ⚠️ KNOWN PITFALL below — DEFAULT: supabase.auth.get_user(token); the auth
           user id is its `id`). On any failure → 401.
         - load the matching profiles row by that user id. If no profile row exists yet, lazily create one
           from the user's email (role="admin"). Return the profile.
     • async def require_screen(authorization, session) -> Screen:
         - extract Bearer token; look up screens where screen_token == token. None → 401. Return the screen.
  app/routers/auth.py   (router prefix "/auth", tag "auth")
     • POST /register  body RegisterIn{email,password,name}:
         - call supabase.auth.admin.create_user({email,password,email_confirm:True}) (service key).
         - insert a profiles row (id = created user id, email, name, role="admin"). Return ProfileRead.
         - on duplicate email → fail("Email already registered","email_taken",409).
     • POST /login  body LoginIn{email,password}:
         - call supabase.auth.sign_in_with_password({email,password}); on failure →
           fail("Invalid credentials","bad_credentials",401).
         - return {"access_token","refresh_token","user":{id,email,name,role}} (look up the profile for name/role).
     • GET /me  (Depends(require_admin)) → the caller's ProfileRead.
  EDIT app/main.py to include the auth router.
  scripts/seed_admin.py  : an httpx script that hits /auth/register to create admin@olrac.com / admin123
                           (idempotent — ignore "already registered").

EXAMPLES:
  POST /auth/login {"email":"admin@olrac.com","password":"admin123"}
   → 200 {"data":{"access_token":"ey...","refresh_token":"...","user":{"id":"uuid","email":"admin@olrac.com",
          "name":"Admin","role":"admin"}},"error":null}
  GET /auth/me  (no header) → 401 {"data":null,"error":{"message":"Not authenticated","code":"unauthenticated"}}

EDGE CASES: missing/expired/garbage JWT → 401 envelope. Wrong audience → 401. Screen token not found → 401.
Register with an email that already exists → 409 envelope (do not 500).

⚠️ KNOWN PITFALL (this is the single most likely "it broke after running" failure): Supabase token verification.
  Newer Supabase projects sign JWTs with ASYMMETRIC keys (ECC/RSA via a JWKS endpoint), so a hardcoded
  jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"]) FAILS with "signature verification failed".
  • DEFAULT (robust, every project): verify with supabase.auth.get_user(token) — returns the user when the
    token is valid regardless of signing method; map its `id` → profiles row; 401 otherwise.
  • OPTIONAL fast path (legacy projects only, where Settings→API shows one shared "JWT Secret"): you MAY use
    jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"). Never hardcode
    this as the ONLY method.

ACCEPTANCE: run scripts/seed_admin.py, then login returns a token; GET /auth/me with that token returns the
profile; GET /auth/me without a token returns the 401 envelope.

OUTPUT RULES: full files only, no ellipses. Briefly note (1 line) how require_admin and require_screen differ.
```

---

## B3 — Content library + Supabase Storage upload  🔵 DeepSeek V4 Flash

```
[PASTE CONTEXT BLOCK §6]

ROLE: Backend engineer. Build the Content library API. Every route is guarded by Depends(require_admin)
and scoped to the caller's owner_id (never return another owner's content).

FILES TO CREATE / EDIT (print fully):
  app/routers/content.py  (prefix "/content", tag "content")
  EDIT app/main.py to include it.

ENDPOINTS — implement EXACTLY:

  GET /content
    Query params (all optional):
      type        : "video" | "image"            → filter content.type
      orientation : "landscape" | "portrait"     → filter content.orientation
      sort        : "newest"(default) | "oldest" | "az" | "za"
                      newest→created_at desc, oldest→created_at asc, az→name asc, za→name desc
      search      : case-insensitive substring match on name (ILIKE %search%)
      tags        : comma-separated; match rows whose tags array OVERLAPS any given tag (&& operator)
    Returns ContentRead[] for owner_id == caller, filtered + sorted.

  POST /content/upload   (multipart/form-data)
    Fields: file (required, UploadFile), name (optional str), tags (optional comma-separated str)
    Steps:
      1. read file bytes; detect content_type from file.content_type:
           image/* → type="image" ; video/* → type="video" ; else → fail("Unsupported file type",
           "bad_type",400).
      2. build storage path "{owner_id}/{uuid4}-{sanitized_filename}".
      3. upload bytes to Supabase Storage bucket "media" at that path (service client; upsert=False;
         set content_type). On storage error → fail("Upload failed","storage_error",502).
      4. get the public URL of the object.
      5. insert a content row: name = name or original filename; type; orientation="landscape"
         (PLACEHOLDER — add a TODO comment: real orientation/duration probing comes later);
         storage_path; public_url; duration_seconds=0; file_size=len(bytes);
         tags = parsed list (split on comma, strip, drop empties).
      6. return ContentRead.

  PATCH /content/{id}   body ContentPatchIn{name?,tags?,start_date?,expiry_date?}
    Update only the provided fields, only if the row's owner_id == caller (else 404
    fail("Content not found","not_found",404)). Return the updated ContentRead.

  DELETE /content/{id}
    If owned: delete the Supabase Storage object at storage_path (ignore "not found" from storage),
    then delete the DB row. Return ok({"ok":True}). If not owned → 404 envelope.

EXAMPLE:
  GET /content?type=video&sort=az
   → {"data":[{"id":"uuid","name":"Demo HD video (beach)","type":"video","orientation":"landscape",
       "public_url":"https://...","duration_seconds":0,"tags":[],"created_at":"..."}],"error":null}

EDGE CASES: no file → 422 (Pydantic/FastAPI) wrapped in the envelope. Unsupported mimetype → 400 envelope.
Patching/deleting a row you don't own → 404 (do not reveal it exists). Empty tags string → tags = [].

⚠️ KNOWN PITFALL: the Storage bucket "media" must already exist and be PUBLIC-READ (created in B1 setup), or
every upload 404s. With supabase-py:
  supabase.storage.from_("media").upload(path, file_bytes, {"content-type": ctype, "upsert": "false"})
  public_url = supabase.storage.from_("media").get_public_url(path)
(get_public_url may return a trailing "?" — strip it before storing.)

ACCEPTANCE: upload a small PNG → row created + file in the "media" bucket + public_url reachable;
GET /content lists it; PATCH renames it; DELETE removes both the row and the storage object.

OUTPUT RULES: full files only, no ellipses, no invented fields.
```

---

## B4 — Screens, pairing handshake, heartbeat, offline sweeper  🟣 Gemini Pro

```
[PASTE CONTEXT BLOCK §6]

ROLE: Backend engineer. Build the screen lifecycle. The pairing handshake is the single most important
flow in the product — comment it step by step.

FIRST (before code): in 5 numbered lines, restate the pairing handshake from the TV's first launch to a
fully paired screen, naming which endpoint each actor calls and what state changes.

FILES TO CREATE / EDIT (print fully):
  app/services/playlist.py  : `async def resolve_playlist_for_screen(session, screen_id) -> list[dict]`
       STUB for now — return the screen's own ordered playlist items joined with content (or [] if none).
       B5 will add the group-override logic. Each item dict: {id, position, duration_override, content:{
       id,name,type,orientation,public_url,duration_seconds}}.
  app/routers/screens.py    (prefix "/screens", tag "screens")
  app/tasks.py              : `async def offline_sweeper(...)` loop (see below)
  EDIT app/main.py : include the screens router; on startup create asyncio.create_task(offline_sweeper()).

ENDPOINTS — implement EXACTLY:

  POST /screens/request-code         (PUBLIC — no auth; called by the TV on first launch)
    1. generate a 6-digit pairing_code; if it collides with an existing pending row, regenerate (loop).
    2. screen_token = generate_screen_token().
    3. insert a screens row: status="pending", pairing_code, pairing_code_expires_at = now()+10min,
       orientation="D0", owner_id=NULL, screen_token, name="Unpaired screen".
    4. return ok({"code": pairing_code, "screen_token": screen_token}).

  POST /screens/pair                 (require_admin)  body PairIn{code, name, orientation in D0..D270}
    1. find the screen WHERE pairing_code == code AND status=="pending" AND pairing_code_expires_at > now().
       None → fail("Invalid or expired code","bad_code",404).
    2. set name=name, orientation=orientation, owner_id=caller.id, status="offline",
       pairing_code=NULL, pairing_code_expires_at=NULL. (Screen will flip to "online" on its first heartbeat.)
    3. return ScreenRead.

  GET /screens/me                    (require_screen)
    → ok({"screen": ScreenRead(self), "playlist": await resolve_playlist_for_screen(session, screen.id)}).
      The TV polls this every 30s. If still pending (not yet paired) return screen with status="pending"
      and playlist=[] so the TV keeps showing its code.

  GET /screens                       (require_admin) → ScreenRead[] for owner_id==caller, newest first,
      including status, last_seen_at, orientation, tags.

  PATCH /screens/{id}                (require_admin) body ScreenPatchIn{name?,description?,orientation?,tags?}
      update provided fields if owned else 404. Return ScreenRead.

  POST /screens/{id}/heartbeat       (require_screen)  — the {id} must equal the token's screen (else 403
      fail("Token/screen mismatch","forbidden",403)). Set last_seen_at=now(), status="online".
      Return ok({"ok":True}).

  DELETE /screens/{id}               (require_admin) — delete if owned (cascade playlist + group_screens).
      Return ok({"ok":True}).

OFFLINE SWEEPER (app/tasks.py): every 30 seconds, in its own AsyncSession, UPDATE screens
  SET status='offline' WHERE status='online' AND last_seen_at < now() - interval '90 seconds'.
  Wrap the loop body in try/except + asyncio.sleep so one DB hiccup never kills the task.

EXAMPLES:
  POST /screens/request-code → {"data":{"code":"483719","screen_token":"k9x..."},"error":null}
  POST /screens/pair {"code":"483719","name":"Lobby Display","orientation":"D0"}
     → {"data":{"id":"uuid","name":"Lobby Display","orientation":"D0","status":"offline",...},"error":null}

EDGE CASES: pairing with a wrong/expired code → 404 envelope. Heartbeat with a token whose screen ≠ {id}
→ 403. /screens/me before pairing → status "pending", empty playlist. Two screens must never share a code.

ACCEPTANCE: full handshake works — request-code → pair → /screens/me shows the screen → heartbeat flips it
online → it shows online in GET /screens → after 90s without heartbeat the sweeper flips it offline.

OUTPUT RULES: full files only, no ellipses. Keep the numbered pairing comment in screens.py.
```

---

## B5 — Playlists, groups, and the resolution rule  🟣 Gemini Pro

```
[PASTE CONTEXT BLOCK §6]

ROLE: Backend engineer. Build playlist + group management and FINISH resolve_playlist_for_screen with the
group-overrides-individual rule. Use transactions for the replace operations.

FIRST (before code): in 3 lines state the resolution rule and what happens for a screen that is in a group
whose group-playlist is empty.

FILES TO CREATE / EDIT (print fully):
  app/routers/playlists.py  (admin)
  app/routers/groups.py     (admin)
  app/services/playlist.py  (REPLACE the B4 stub with the full version)
  EDIT app/main.py to include both routers.

PLAYLISTS — implement EXACTLY:

  GET /screens/{id}/playlist     (require_admin, owned else 404)
     → the screen's playlist items ordered by position asc, each joined with its full content row.
       If the screen has no playlist row → return [].

  PUT /screens/{id}/playlist     (require_admin, owned else 404)
     body PlaylistPutIn{items: [{content_id, position, duration_override?}]}
     In ONE transaction:
       1. get-or-create the playlist row for this screen (screen_id set, group_id NULL).
       2. delete all existing playlist_items for that playlist.
       3. insert the new items (validate every content_id is owned by the caller; if any isn't →
          rollback + fail("Unknown content in playlist","bad_content",400)).
       4. set playlists.updated_at = now().
     Return the saved items (same shape as GET).

GROUPS — implement EXACTLY (all admin, scoped to owner_id):

  GET /groups        → Group[] each with: id, name, created_at, screens (joined ScreenRead list via
                       group_screens), has_playlist (bool).
  POST /groups       body GroupCreateIn{name, screen_ids[]}: create the group (owner_id=caller) + one
                     group_screens row per screen_id (validate each screen is owned). Return GroupRead.
  PATCH /groups/{id} body GroupPatchIn{name?, screen_ids?}: rename and/or REPLACE membership
                     (delete old group_screens, insert new) in a transaction. Return GroupRead.
  PUT /groups/{id}/playlist  body PlaylistPutIn{items:[...]}: same get-or-create + replace-in-transaction
                     logic as the screen playlist, but the playlist row has group_id set (screen_id NULL).
  DELETE /groups/{id}  → delete group (cascade its playlist + group_screens). ok({"ok":True}).

RESOLUTION (app/services/playlist.py):
  async def resolve_playlist_for_screen(session, screen_id) -> list[dict]:
     1. find the groups this screen belongs to (via group_screens).
     2. if it belongs to a group whose playlist EXISTS and HAS ≥1 item → use that group playlist.
     3. else → use the screen's own playlist (or [] if none).
     4. return items ordered by position, each as
        {id, position, duration_override, content:{id,name,type,orientation,public_url,duration_seconds}}.
     This is exactly what GET /screens/me serves to the TV.

EXAMPLE:
  PUT /screens/{id}/playlist {"items":[{"content_id":"c1","position":0},
                                       {"content_id":"c2","position":1,"duration_override":15}]}
   → {"data":[{"id":"...","position":0,"duration_override":null,"content":{...}},
              {"id":"...","position":1,"duration_override":15,"content":{...}}],"error":null}

EDGE CASES: a content_id not owned by the caller anywhere in items → 400, whole PUT rolled back (no partial
writes). Resolving a screen in a group with an empty group-playlist → falls through to the screen's own
playlist. Deleting a group must not delete its member screens, only the membership + group playlist.

ACCEPTANCE: PUT a screen playlist then GET it back identical; create a group containing that screen, give the
group a different playlist, and confirm GET /screens/me now returns the GROUP playlist (override works);
empty the group playlist and confirm it falls back to the screen's own.

OUTPUT RULES: full files only, no ellipses. Replace the stub completely; don't leave both versions.
```

---

## B6 — Playback logging + reports + CSV export  🔵 DeepSeek V4 Flash

```
[PASTE CONTEXT BLOCK §6]

ROLE: Backend/data engineer. Build playback logging (written by screens) and the Proof-of-Play reporting
API (read by admins). Use SQL aggregation, not Python loops.

FILES TO CREATE / EDIT (print fully):
  app/routers/playback.py   (POST /playback/log — require_screen)
  app/routers/reports.py    (the GET /reports/* — require_admin)
  EDIT app/main.py to include both.

ENDPOINTS — implement EXACTLY:

  POST /playback/log   (require_screen)  body: list[PlaybackLogIn]  where
      PlaybackLogIn = {content_id: uuid, played_at: datetime(ISO8601), duration_played: int>=0}
    Bulk-insert one playback_logs row per entry, with screen_id = the token's screen. Ignore entries whose
    content_id doesn't exist (skip, don't fail). Return ok({"ok":True,"inserted":n}).

  Common to all reports: query params from, to (ISO datetimes; default = last 7 days if omitted). Always
  restrict to playback_logs whose screen belongs to the caller (join screens on owner_id) and
  played_at BETWEEN from AND to.

  GET /reports/summary    → group by content_id:
      [{content_id, name, type, screen_count: COUNT(DISTINCT screen_id), play_count: COUNT(*),
        total_duration: SUM(duration_played)}]  ordered by play_count desc.
  GET /reports/by-screen  → group by screen_id:
      [{screen_id, screen_name, play_count, total_duration}] ordered by play_count desc.
  GET /reports/hourly     → group by (screen_id, date_trunc('hour', played_at)):
      [{screen_id, screen_name, hour(ISO), play_count, total_duration}] ordered by hour asc.
  GET /reports/export?type=summary|by-screen|hourly
      → the SAME data as the matching endpoint, streamed as text/csv with a header row and
        Content-Disposition: attachment; filename="olrac-report-{type}.csv". Use StreamingResponse + csv module.

EXAMPLE:
  GET /reports/summary  → {"data":[{"content_id":"c1","name":"Beach","type":"video","screen_count":2,
       "play_count":57,"total_duration":456}],"error":null}

EDGE CASES: no logs in range → empty list (200, not error). from > to → empty list. duration_played
negative → reject that one entry (Pydantic ge=0). Export with an unknown type → fail("Unknown report
type","bad_type",400).

ACCEPTANCE: POST a few logs as a screen, then GET /reports/summary shows the aggregated counts; the CSV
export downloads with the correct rows and header.

OUTPUT RULES: full files only, no ellipses. Prefer SQLAlchemy func.count / func.sum / date_trunc over Python.
```

---

## B7 — Websites + final wiring + smoke test  🟡 MiMo V2.5 / 🟢 Nemotron 3 Ultra

```
[PASTE CONTEXT BLOCK §6]

ROLE: Backend engineer. Build the small Websites CRUD, finish wiring the app, and write an end-to-end smoke
test that proves the whole loop.

FILES TO CREATE / EDIT (print fully):
  app/routers/websites.py   (admin, scoped to owner_id)
     GET /websites           → Website[] newest first.
     POST /websites {name,url}→ validate url starts with http:// or https:// (else fail("Invalid URL",
                                "bad_url",400)); insert; return WebsiteRead.
     DELETE /websites/{id}    → delete if owned else 404; ok({"ok":True}).
  EDIT app/main.py : confirm ALL routers are included (auth, content, screens, playlists, groups, playback,
     reports, websites); CORS allows both Vite origins; the global exception handler is registered; the
     offline-sweeper startup task is running. Remove any leftover import-guards now that every module exists.
  scripts/smoke_test.py : a single httpx script (prints PASS/FAIL + a final summary). Steps, in order:
     1. register (ignore 409) + login admin → capture access_token.
     2. POST /content/upload a tiny in-memory PNG → capture content id.
     3. POST /screens/request-code (no auth) → capture code + screen_token.
     4. POST /screens/pair {code,"name":"Smoke Screen","orientation":"D90"} as admin → capture screen id.
     5. PUT /screens/{id}/playlist with the uploaded content at position 0.
     6. GET /screens/me with the screen_token → assert status paired + the content item present.
     7. POST /screens/{id}/heartbeat with the screen_token → assert ok.
     8. POST /playback/log [{content_id, played_at=now, duration_played=8}] with the screen_token.
     9. GET /reports/summary as admin → assert play_count >= 1 for that content.
     Exit non-zero if any step fails.

ACCEPTANCE: `python scripts/smoke_test.py` prints PASS for all 9 steps against a running server + a clean
Supabase project.

OUTPUT RULES: full files only, no ellipses. The smoke test must be runnable as-is (configurable BASE_URL,
default http://localhost:8000).
```

**✅ Phase 1 is done when `python scripts/smoke_test.py` prints PASS for all 9 steps.**

---
---

# PHASE 2 — ADMIN APP PROMPTS (Claude Code)

> The admin app already exists in `admin/` (React 18 + Vite + TS + zustand + react-router-dom v6, mock data layer). Run these in Claude Code. Each prompt is a full spec: use it to regenerate from scratch, extend a page, or swap the mock layer for the real API. Tell Claude Code to read `@admin.html` (the visual source of truth) and the existing files in `admin/src`.

---

## A1 — Scaffold, design tokens, app shell, routing  (Claude Code)

```
Build the foundation of the Olrac Signage ADMIN web app (React 18 + Vite + TypeScript). Read @admin.html —
match its layout, spacing, colours and fonts EXACTLY. Use the existing tokens; introduce no new colours.

STACK & DEPS: react, react-dom, react-router-dom@6, zustand@4, vite, @vitejs/plugin-react, typescript.
(Icons = inline SVG + emoji, as in @admin.html — do not add an icon library. Styling = a single ported CSS
file, NOT Tailwind, so it is pixel-identical to the reference.)

FILES TO PRODUCE:
  package.json (scripts: dev/build/preview/typecheck; dev server on port 5173)
  vite.config.ts (react plugin; server.port 5173)
  tsconfig.json (strict, jsx react-jsx, bundler resolution, noEmit)
  index.html (mount #root; load Outfit + JetBrains Mono from Google Fonts)
  src/main.tsx (BrowserRouter > App; import ./styles.css)
  src/styles.css (PORT THE ENTIRE <style> BLOCK FROM @admin.html VERBATIM into CSS variables + classes:
     :root tokens --accent #1E293B etc; .sb/.nav/.ni sidebar; .topbar; .btn variants; .mc/.scc cards; .mo/.md
     modals; .og orientation picker; .pill/.pg/.pa/.pr/.ps; .toast; plus a .login-wrap/.login-card block.)
  src/types.ts (Media, Screen, Group, Website, Toast — see DATA SHAPES below)
  src/store.ts (zustand store — see STORE below)
  src/lib/mock.ts (seedMedia[6], seedScreens[3], seedWebsites[1] — copy the demo data from @admin.html)
  src/components/Sidebar.tsx (232px fixed sidebar: Olrac badge + "Signage Platform"; nav groups
     "Main" [Dashboard /, Content /content, Screens /screens, Groups /groups, Websites /websites] and
     "Admin" [Reports /reports, Activity /activity, Alerts /alerts with red badge "2"]; active item gets the
     dark-slate .ni.active style; the Screens item also stays active on /playlist; user chip "R / Admin /
     Super Admin" pinned to the bottom. Use useLocation + useNavigate.)
  src/components/Topbar.tsx (56px bar: page title derived from pathname via a titles map; search box; 🌙 and
     bell icon buttons.)
  src/components/ToastHost.tsx (reads store.toasts, renders the .tc/.toast stack bottom-right.)
  src/App.tsx (Routes: /login → Login; everything else nested under a <Shell/> (Sidebar + Topbar +
     <Outlet/> inside .cnt) guarded by <Protected> which reads store.authed and redirects to /login;
     "*" → redirect to /. Render <ToastHost/> once at the App root.)

DATA SHAPES (src/types.ts):
  Media   {id; name; type:'Video'|'Image'; orient:'landscape'|'portrait'; dur:string|null; ico:string; bg:string}
  Screen  {id; name; status:'online'|'offline'; lastSeen:string; orientLabel:string; deg:0|90|180|270; description?}
  Group   {id; name; screens:string[]}
  Website {id; name; addedAt:string}
  Toast   {id:number; msg:string; type:'success'|'error'}

STORE (src/store.ts, zustand): authed(boolean, persisted to localStorage 'olrac_authed') + login()/logout();
data slices media/screens/groups/websites seeded from mock; selectedScreen(string, default 'Lobby Display')
+ selectScreen(name); toasts[] + pushToast(msg,type='success') (auto-dismiss after 3000ms) + dismissToast(id);
actions addMedia, addScreen, addGroup, removeGroup(id), addWebsite.

ACCEPTANCE: `npm run dev` → sidebar navigation switches pages with the .fi fade; the active nav item matches
the route; refreshing while logged out redirects to /login; `npm run typecheck` and `npm run build` are clean.
Deliver complete files.
```

---

## A2 — API client + React Query hooks (swap the mock for the real backend)  (Claude Code)

```
The admin app currently uses an in-memory zustand mock (src/store.ts). Wire it to the real Olrac API
(contract below) WITHOUT changing any page's JSX — pages keep calling hooks; only the data source changes.

ADD DEPS: @tanstack/react-query, axios, @supabase/supabase-js.

FILES TO PRODUCE:
  src/lib/supabase.ts — a supabase-js client from VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY, used ONLY for
     auth (signInWithPassword, getSession, signOut). All other data goes through our FastAPI.
  src/api/client.ts — an axios instance (baseURL = VITE_API_URL). Request interceptor attaches the Supabase
     access_token as `Authorization: Bearer …`. Response interceptor: on 401, sign out + redirect to /login.
     Unwrap the {data,error} envelope: return resp.data.data, or throw resp.data.error.
  src/api/*.ts — typed modules, one function per endpoint in §4: auth, content, screens, playlists, groups,
     reports, websites. Full TS types matching the backend (snake_case from the API mapped to the camelCase
     UI types in src/types.ts via small adapters).
  src/hooks/*.ts — React Query wrappers:
     queries:  useContent(filters), useScreens() (refetchInterval 30000 so the online badge is live),
               usePlaylist(screenId), useGroups(), useReports(kind,range), useWebsites(), useMe().
     mutations: useLogin, useLogout, useUploadContent, useDeleteContent, usePairScreen, useUpdateScreen,
               useSavePlaylist, useCreateGroup, useUpdateGroup, useDeleteGroup, useAddWebsite, useDeleteWebsite
               — each invalidates the relevant query keys on success and pushes a success/error toast.
  src/main.tsx — wrap <App/> in a QueryClientProvider.
  .env.example — VITE_API_URL=http://localhost:8000, VITE_SUPABASE_URL=…, VITE_SUPABASE_ANON_KEY=…

KEY RULE: keep React Query server state and any local editing state separate (e.g. the playlist editor's
working array) so a 30-second background refetch never overwrites unsaved edits.

[PASTE §3 DATA MODEL + §4 API CONTRACT]

ACCEPTANCE: login uses Supabase auth and stores the token; the content/screens/groups/websites pages render
live API data; the screens page's online badge updates within ~30s; 401 bounces to /login. Deliver full files.
```

---

## A3 — Login + Content library  (Claude Code)

```
Build/refine two admin pages, matching @admin.html exactly. Files: src/pages/Login.tsx, src/pages/Content.tsx,
and reuse src/components/{MediaCard,SortMenu,UploadModal}.tsx.

1) LoginPage (/login): a centered .login-card on a faint grid background (.login-bg). Brand row (Olrac badge),
   "Sign in to Olrac Signage" title, email + password fields (.fi2), a full-width dark-slate submit button.
   On submit call the login mutation (useLogin / Supabase auth), store the session, redirect to /. Pre-fill
   admin@olrac.com / admin123 with a "demo build" hint line. Empty fields → an error toast.

2) ContentPage (/content): header ".sh" with title "Content library" and a toolbar: <SortMenu/> (options:
   Date added newest/oldest, Alphabetical A–Z / Z–A, Start date, Expiry date), a "⚡ Filters" toggle, and a
   dark "+ Upload Files" button. The Filters panel (.fp) has Media-type toggle chips (Videos/Images) and
   Orientation toggle chips (Landscape/Portrait) using .tb2/.tb2.active, plus Reset + Apply. Filtering is live
   against useContent. The grid (.mg) renders <MediaCard/> for each item: thumbnail (.mth with emoji on a
   coloured bg), a duration .mbadge for videos, a ▶/📷 .mtype icon, name, "type · orientation · time", and a
   hover ⋮ menu. Show a loading skeleton and an empty state.

   UploadModal: the .dz drag-and-drop dropzone (highlight on dragover via a .dov class), a hidden multi-file
   <input accept="video/*,image/*">, Cancel + Upload. On drop/select call useUploadContent (multipart) and
   push a toast.

ACCEPTANCE: filters instantly narrow the grid; the upload modal opens, accepts files, posts them, closes, and
toasts; everything matches @admin.html spacing/colours. Deliver full files.
```

---

## A4 — Screens page + 3-step pairing wizard (with orientation)  (Claude Code)

```
Build the Screens page and the Add-Screen wizard, matching @admin.html EXACTLY. The orientation step is the
signature feature — reproduce the 2×2 picker precisely. Files: src/pages/Screens.tsx,
src/components/{ScreenCard,PairWizard,SettingsModal}.tsx.

1) ScreensPage (/screens): ".sh" header "Screens" + "↕ Sort" + dark "+ Add Screen" button. Grid (.sg) of
   <ScreenCard/>. Each card: a dark gradient .sth thumbnail showing the screen name (or dimmed "Offline"),
   an online/offline .sstat pill, then .sinf with name, "lastSeen · orientLabel · deg°", and two buttons
   (Edit Playlist → navigate to /playlist after selectScreen(name); Settings → open SettingsModal). Clicking
   the card body also opens the playlist. Use useScreens() with refetchInterval 30000 so the badge is live.
   IMPORTANT: the .sac button row must stopPropagation so button clicks don't also trigger the card navigation.

2) AddScreenWizard (modal, 3 steps with the .wsteps stepper header):
   STEP 1 "Enter code": a .pair-hint instruction, 3 platform pills (.pb3 Google Play / Amazon / BrightSign),
     a big monospace pairing-code input (JetBrains Mono, font-size 22, letter-spacing 5, centered), and a
     screen-name input. "Next →" validates: code length ≥4 and a non-empty name (else error toast).
   STEP 2 "Orientation": a 2×2 .og grid of 4 .oc cards — Landscape +0° (🖥️), Portrait +90° (📱), Upside Down
     +180° (🖥️ rotated 180°), Reverse Portrait +270° (📱 rotated 180°). Each shows the emoji (.oico), label
     (.olbl), and degree in mono (.odeg). Clicking selects it (.oc.sel highlight). Default = Landscape. Back +
     "Pair Screen".
   STEP 3 "Done": ✅, "\"{name}\" paired successfully!", and "Orientation: {label} ({deg}°) — content will
     start playing shortly.", then "Go to Screens" which closes the modal. On pairing call usePairScreen(
     {code,name,orientation:D0|D90|D180|D270}); the new screen appears in the grid.
   RESET the wizard to step 1 every time it opens (useEffect on `open`).

3) SettingsModal: CONTROLLED inputs (orientation <select> of all four, name, description, tags) seeded from
   the passed Screen via a useEffect that resaves when the modal opens — because the modal stays mounted and
   uncontrolled defaultValue would show stale data for the wrong screen. Save calls useUpdateScreen + toast.

ACCEPTANCE: the wizard walks 1→2→3, the orientation highlight works, a paired screen shows the chosen
orientation/deg on its card; opening Settings on different screens shows each screen's own values. Full files.
```

---

## A5 — Playlist editor (click-to-add, drag reorder, dirty-state save)  (Claude Code)

```
Build the Playlist Editor — the most complex page — matching @admin.html. File: src/pages/PlaylistEditor.tsx.

LAYOUT (.pl-layout, grid 1fr 330px, height calc(100vh - 148px)):
  HEADER: "← Back" (→ /screens), the selected screen's name + "orientLabel · deg° · description", an
    online/offline .pill, "⚙ Settings" (opens SettingsModal), "⏰ Hours".
  LEFT panel (.pl-panel): header "Playlist" + a "Save Changes" button that is greyed/disabled
    (opacity .35, pointer-events none) until the working playlist is DIRTY. Body: if empty, the .pl-empty
    state ("Click + on items from the right…"); else the list of .pl-item rows — drag handle ⠿, thumbnail,
    name, "type · orient", optional .pid duration, and a .prm ✕ remove.
  RIGHT panel (.lib-panel): header "Content library" + ↑/↕/⚡ buttons; body lists the content library as .li
    rows; clicking a row (or its green .ladd +) APPENDS a copy to the working playlist.

STATE: keep the working playlist in LOCAL component state (seeded once from usePlaylist(screenId)); track a
`dirty` boolean. The selected screen comes from store.selectedScreen (find it in useScreens()).
  • add(item): push a copy with a fresh unique id; dirty=true; toast "Added …".
  • remove(i): splice; dirty=true.
  • reorder via NATIVE HTML5 drag-and-drop: onDragStart sets the index AND e.dataTransfer.setData('text/plain',i)
    + effectAllowed='move' (Firefox needs dataTransfer set or the drag never starts); onDragOver preventDefault;
    onDrop moves the item; add a .dragging class to the row being dragged.
  • save(): call useSavePlaylist (PUT /screens/{id}/playlist with content_id+position+duration_override);
    dirty=false; toast "Playlist saved!".
CRITICAL: never let a background refetch overwrite the local working array while dirty.

ACCEPTANCE: clicking + adds items; dragging reorders (also in Firefox); ✕ removes; Save is disabled until a
change is made and re-disables after saving. Deliver the full file.
```

---

## A6 — Groups (inline add form) + Websites  (Claude Code)

```
Build two admin pages, matching @admin.html. Files: src/pages/Groups.tsx, src/pages/Websites.tsx,
src/components/WebsiteModal.tsx.

1) GroupsPage (/groups): ".sh" header + "+ Add Screen Group". The button reveals an INLINE .new-grp form
   (not a modal): a group-name input and a .scl checkbox list of every screen (name + "status · orientLabel ·
   deg°"); "Create Group" (validates non-empty name; calls useCreateGroup with the checked screen names;
   toast) and "Cancel". Below, a .grp-grid of group cards (.gc): 📺 icon, name, "{n} screen(s)", the assigned
   screens as .st chips (or "No screens assigned"), and "Edit Playlist" + a red "Remove" (useDeleteGroup +
   confirm + toast). When there are no groups AND the form is closed, show the .empt empty state with its own
   "+ Add Screen Group" button.

2) WebsitesPage (/websites): ".sh" header + <SortMenu/> + "+ Add Website". A .mg grid of website cards (globe
   on #F0F9FF, name, "Website · addedAt", ⋮). WebsiteModal (small): name + URL inputs; Add validates a
   non-empty name (and ideally an http(s) URL) → useAddWebsite + toast.

ACCEPTANCE: creating a group shows it in the grid with its screen chips; removing it returns to the empty
state; adding a website prepends a card. Deliver full files.
```

---

## A7 — Reports + Activity + Alerts + Dashboard  (Claude Code)

```
Build the four remaining admin pages, matching @admin.html. Files: src/pages/{Reports,Activity,Alerts,
Dashboard}.tsx, src/components/ExportModal.tsx.

1) ReportsPage (/reports): header "Playback report" + a "1 screen reporting" .ps pill + "Enable Reporting".
   A controls row: a date-range <select> (Last 7 days / 30 days / This month), "↺ Refresh", "↓ Export"
   (opens ExportModal), "⚡ Filters". A .tw/.gt table with columns Item, Type, Screens, Play count, Total
   duration, fed by useReports('summary',range). When there is no data show the single-row "Screens report
   playback data periodically…" message. ExportModal (small): 3 radio options (Summary / Per-screen breakdown
   / Hourly detail) with the first pre-selected and highlighted; Export hits /reports/export?type=… and
   downloads the CSV (then toast).

2) ActivityPage (/activity): a .tw/.gt table (Time, User avatar+name, coloured action .pill, Target). Static
   demo rows are fine until an activity endpoint exists.

3) AlertsPage (/alerts): header + "+ New Alert". A column of alert cards — offline screen (red border,
   #FECACA, 🔴) and expiring content (amber, #FDE68A, ⚠️) — each with title, sub, and a "Dismiss" button that
   removes it from local state. Empty state when none remain.

4) DashboardPage (/): a 4-card .stats-row (Total screens, Online now, Content items, Plays today) wired to
   live useScreens()/useContent() counts; a "Screens" section (.sg of <ScreenCard/>, "View all" → /screens);
   a "Recent content" section (.mg of the first 4 <MediaCard/>, "View all" → /content).

ACCEPTANCE: the export modal downloads a CSV; alerts dismiss; the dashboard counts reflect live data. Full files.
```

**✅ Phase 2 done when:** you can log in, upload content, pair a screen with an orientation, build & save a playlist, create/remove a group, add a website, and export a report — all against the running backend.

---
---

# PHASE 3 — TV PLAYER PROMPTS (Claude Code · web kiosk)

> The TV app already exists in `tv/` (React 18 + Vite + TS, a pair→connecting→player→offline state machine). Run these in Claude Code; tell it to read `@tv-player.html` (visual source of truth) and the files in `tv/src`.

---

## T1 — Scaffold + theme + screen state machine  (Claude Code)

```
Build the foundation of the Olrac Signage TV PLAYER web-kiosk app (React 18 + Vite + TS), designed to run
fullscreen in a browser / Android WebView. Read @tv-player.html — match it EXACTLY (dark #0F172A, glass
cards, Outfit + JetBrains Mono, NO purple).

STACK: react, react-dom, vite, @vitejs/plugin-react, typescript. (Later prompts add axios + idb for the real
API + caching.) Dev server on port 5174.

FILES TO PRODUCE:
  package.json / vite.config.ts (port 5174) / tsconfig.json / index.html (load the two fonts) / src/main.tsx
  src/styles.css — PORT THE ENTIRE <style> BLOCK FROM @tv-player.html. Because React renders one screen at a
     time, convert the #scr-pair/#scr-conn/#scr-player/#scr-off id rules into a base ".scr{position:fixed;
     inset:0;z-index:10}" plus per-screen classes (.scr-pair flex-center, .scr-conn flex-col-center, .scr-off
     flex-col-center, .scr-player block). Keep ALL the rest verbatim: .pair-card glass, .pd digit boxes + the
     `pb` border pulse, .pair-bg-lines grid, .slide/.s0..s4 themes, .slide-emoji/.slide-caption, the .hud
     (clock + Online badge), .prog-bar/.prog-fill, .dots, .remote (.rb/.exit-b), the .spin connecting spinner,
     the offline block, and the fadeUp entrance animation.
  src/data.ts — the demo "playlist": SLIDES[5] ({emoji,title,sub,cls:'s0'..'s4'}), SLIDE_DURATION=5000,
     SCREEN_NAME='Lobby Display', SCREEN_ORIENTATION_DEG=0. (Production replaces this with the resolved
     playlist from GET /screens/me.)
  src/screens/{Pairing,Connecting,Offline,Player}.tsx (Player is built fully in T3 — a stub is fine here)
  src/App.tsx — a state machine with 4 states: 'pair' | 'conn' | 'player' | 'offline'. 'conn' is transitional:
     a useEffect auto-advances 'conn' → 'player' after ~1.8s (standing in for "fetch playlist + cache"). Render
     exactly one screen for the current state.

ACCEPTANCE: `npm run dev` shows the pairing screen; build + typecheck are clean. Deliver full files.
```

---

## T2 — Pairing screen + auto-transition to the player  (Claude Code)

```
Build the TV pairing flow, matching the @tv-player.html pairing card EXACTLY: the glass .pair-card on the
.pair-bg-lines grid, the brand row (📺 "Olrac Signage" / "DIGITAL DISPLAY SYSTEM"), the "Pairing Code" label,
six .pd digit boxes split 3 + .psep + 3 with the pulsing border animation, the multi-line instruction, the
three platform pills, and the action button. File: src/screens/Pairing.tsx (+ a small pairing service).

DEMO behaviour (what ships now): show a fixed code (e.g. 4 8 3 / 7 1 9) and a "▶ Simulate Pairing (Demo)"
button that calls onPair() to move App into 'conn'.

PRODUCTION behaviour (leave this wired behind a flag / TODO so it's ready):
  1. On first launch POST /screens/request-code → store {code, screen_token} in localStorage; render the
     returned 6 digits in the .pd boxes (replace the demo button with the live code).
  2. Poll GET /screens/me (Bearer screen_token) every 5s. While screen.status === 'pending', keep showing the
     code. When it flips to 'offline'/'online' (admin paired it), call onPair() → 'conn' → 'player'.
  3. If the 10-minute code expires (poll returns bad_code), request a fresh code automatically.
  4. On boot, if a screen_token + an already-paired screen exist in storage, SKIP pairing → go straight to
     the player.

ACCEPTANCE (demo): clicking Simulate Pairing animates to Connecting then the Player. The component is
structured so swapping the demo button for the live request-code + polling is a small, contained change.
Deliver the full file(s).
```

---

## T3 — Player engine: rotate, loop, progress, HUD, remote (+ caching hooks)  (Claude Code)

```
Build the core TV player engine, matching @tv-player.html. File: src/screens/Player.tsx. This is the heart of
the app — implement it carefully and keep the timing smooth.

RENDER:
  • A ".rot" stage wrapping all slides, rotated to the screen orientation. rotStyle(deg): for 0/180 →
    width/height 100% + rotate(deg); for 90/270 → width:100vh; height:100vw; left/top 50%; transform:
    translate(-50%,-50%) rotate(deg) (swap dimensions so the rotated content still fills the viewport).
  • All SLIDES rendered absolutely; the current one gets ".active" (opacity crossfade .9s). Each slide shows
    the big .slide-emoji and a .slide-caption (.cap-title + .cap-sub) over its .s0..s4 gradient.
  • HUD (.hud, toggle ".vis"): left = 📺 "Olrac Signage · {SCREEN_NAME}"; right = a JetBrains-Mono clock
    (HH:MM, updated every second) + an "Online" status pill with the blinking .hud-dot.
  • .prog-bar/.prog-fill at the bottom; .dots indicator; the .remote (◀, ℹ toggle HUD, ⏸/▶ pause, ▶, "✕ Exit").

ENGINE:
  • Advance through SLIDES on a loop. Drive the progress bar + auto-advance with ONE requestAnimationFrame
    loop in a useEffect keyed on [cur, paused]; compute elapsed via performance.now(); write width directly to
    the .prog-fill ref (don't re-render every frame); when elapsed ≥ duration, reset and advance to the next
    slide. Respect `paused` (freeze progress; resume from where it left off using a stored elapsed value).
    Use duration_override ?? duration ?? SLIDE_DURATION per item.
  • Navigation: next/prev wrap modulo N and reset progress. Manual nav resets elapsed to 0.
  • HUD auto-hides ~4s after it appears; ℹ / the `i` key toggles it; it re-shows on interaction.
  • Keyboard: ←/→ prev/next, Space pause (preventDefault), i toggle HUD, Esc → onExit(). Touch: horizontal
    swipe >55px → prev/next.

PRODUCTION hooks (wire as TODO-ready, don't break the demo):
  • POLL: every 30s GET /screens/me; if the resolved playlist changed (compare item ids + updated_at), reload.
  • CACHE/OFFLINE: download each item's public_url and store the blob in IndexedDB keyed by content id +
    updated_at; only re-download if missing; PLAY FROM THE CACHED BLOB URL so playback survives a network
    drop. On a failed poll keep playing the cache and show the .scr-off offline screen; retry in the
    background and return to the player on success. Render videos via <video> (play to ended), images for
    their duration.

ACCEPTANCE (demo): slides crossfade and loop on a 5s timer; the progress bar tracks each slide; pause freezes
and resumes correctly; arrows/space/i/esc + swipe + the on-screen remote all work; changing
SCREEN_ORIENTATION_DEG to 90 rotates the whole stage and still fills the screen. Deliver the full file.
```

---

## T4 — Heartbeat + playback reporting  (Claude Code)

```
Add the TV's background reporting so the admin dashboard shows live status + Proof-of-Play. These run while
media plays and must not interrupt it. Files: src/services/heartbeat.ts, src/services/playbackLogger.ts, and
the wiring into src/screens/Player.tsx.

  1. HEARTBEAT: every 30s POST /screens/{id}/heartbeat with the screen_token (keeps the screen 'online' in
     the admin). Keep firing for as long as the player is mounted.
  2. PLAYBACK LOG: when each item finishes playing, record {content_id, played_at:ISO, duration_played:sec}.
     Batch entries and POST /playback/log every 60s OR when the batch reaches 20 entries. If offline, queue
     entries in localStorage and flush them when connectivity returns.
  3. Wrap both in a single background service started on Player mount and torn down on unmount (clear the
     intervals; flush any pending logs on unmount).

ACCEPTANCE: with the backend running, a playing TV shows 'online' in the admin within ~30s, and play counts
appear in Reports after the first flush. Deliver full files.
```

**✅ Phase 3 (web app) done when:** a paired browser/WebView plays its playlist rotated to its orientation,
shows Online in the admin within ~30s, keeps playing when the network is cut, and produces play counts in Reports.

---

## T5 — Android-TV WebView kiosk wrapper (native shell)  (Claude Code) — optional, recommended for real TVs

> This is the ONLY thing we take from `litrik/displayer` — its **deployment model** (launcher + auto-start +
> unattended fullscreen), realised as a thin native Kotlin shell that simply hosts our already-built React TV
> web app. We do NOT port displayer's Compose JSON renderer or Ktor server.

```
Build a MINIMAL native Android TV "kiosk wrapper": one Kotlin Activity + a WebView that displays our deployed
Olrac Signage TV web app (the Vite build in tv/) fullscreen, unattended, auto-starting on boot. Do NOT
reimplement any playback logic — the web app already does slides, rotation, caching, heartbeat and reporting.
This shell only hosts it.

TARGET: Android TV / Fire TV (Leanback). minSdk 21. Gradle Kotlin DSL. applicationId com.olrac.signage.tv.

FILES TO PRODUCE (a complete, buildable Android Studio project):
  settings.gradle.kts · build.gradle.kts (root) · app/build.gradle.kts (a BuildConfig field TV_URL from
    gradle.properties) · gradle.properties (TV_URL=https://your-deployed-tv.example.com)
  app/src/main/AndroidManifest.xml
  app/src/main/java/com/olrac/signage/tv/MainActivity.kt
  app/src/main/java/com/olrac/signage/tv/BootReceiver.kt
  app/src/main/res/values/{strings.xml,themes.xml} (a fullscreen, no-action-bar theme)
  app/src/main/res/drawable/banner.xml (a simple TV launcher banner)
  README.md (build, sideload, and kiosk-lock instructions — see KIOSK)

MainActivity (the whole app):
  • Create a WebView, setContentView(it). settings: javaScriptEnabled=true, domStorageEnabled=true,
    mediaPlaybackRequiresUserGesture=false (AUTOPLAY video), cacheMode=LOAD_DEFAULT. Set a WebViewClient +
    WebChromeClient. loadUrl(BuildConfig.TV_URL).
  • IMMERSIVE FULLSCREEN via WindowInsetsControllerCompat: hide status + nav bars
    (BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE) and re-hide on focus.
  • KEEP AWAKE: window.addFlags(FLAG_KEEP_SCREEN_ON) so the panel never sleeps.
  • RESILIENCE: onReceivedError/onReceivedHttpError → show a small retry overlay and reload after a few
    seconds; a ConnectivityManager.NetworkCallback that reloads when the network returns; optional periodic
    reload (e.g. every 6h). Swallow BACK (override onBackPressed to do nothing) so the kiosk can't be exited.

AndroidManifest:
  • <uses-feature android:name="android.software.leanback" android:required="true"/>
  • <uses-feature android:name="android.hardware.touchscreen" android:required="false"/>
  • permissions: INTERNET, ACCESS_NETWORK_STATE, WAKE_LOCK, RECEIVE_BOOT_COMPLETED.
  • MainActivity intent-filters (displayer's auto-start mechanism — BE the launcher):
      MAIN + LEANBACK_LAUNCHER (shows on the Android TV home row), and MAIN + HOME + DEFAULT (so it can be set
      as the Home app → starts on boot). android:banner on <application>; activity screenOrientation=
      sensorLandscape (the web app handles content rotation).
  • BootReceiver: a <receiver> for android.intent.action.BOOT_COMPLETED that starts MainActivity with
    FLAG_ACTIVITY_NEW_TASK (belt-and-braces auto-start).

KIOSK lock (document in README — the displayer trick):
  • Easiest: after install press Home → set "Olrac Signage TV" as the default Home app.
  • Or via ADB disable the stock launcher:  adb shell pm disable-user --user 0 com.google.android.tvlauncher
    (re-enable with:                         adb shell pm enable com.google.android.tvlauncher)
  • (Optional, managed devices) mention Android screen-pinning / lock-task mode.

WHAT WE DELIBERATELY DO NOT TAKE FROM displayer: its Jetpack Compose JSON renderer, its Ktor admin server, and
its weather/region layout — our React TV app + FastAPI already provide rendering, control and content.

ACCEPTANCE: builds to an APK; sideloaded onto an Android TV emulator/box it launches fullscreen into the
deployed TV web app, hides the system bars, keeps the screen on, recovers on network loss, and — once set as
Home or with the stock launcher disabled — relaunches automatically after a reboot. Deliver every file in full.
```

**✅ Phase 3 (on-device) done when:** the wrapper APK auto-launches the TV web app fullscreen on a real
Android TV / Fire TV after a reboot and survives a network blip.

---
---

# PHASE 4 — INTEGRATION & DEPLOY

## I1 — End-to-end local wiring + manual test  (Claude Code or you)

```
Wire the three apps together locally and verify the full loop.

1. .env files:
   backend (.env): SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET, DATABASE_URL,
     SCREEN_TOKEN_SECRET, CORS_ORIGINS="http://localhost:5173,http://localhost:5174".
   admin (admin/.env): VITE_API_URL=http://localhost:8000, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY.
   tv (tv/.env): VITE_API_URL=http://localhost:8000.
2. Confirm FastAPI CORS allows both Vite origins. Run all three: uvicorn on :8000, admin on :5173, tv on :5174.
3. MANUAL TEST (in order): register/login → upload content → open the TV (it shows a code) → pair it in admin
   with Portrait/90° → build + save a playlist → confirm the TV plays it rotated → confirm the TV shows Online
   in admin within ~30s → wait for a playback flush → confirm Reports shows the play count.
4. Provide a docker-compose.yml that runs just the FastAPI backend (Postgres is Supabase-hosted) for a
   one-command start, plus the exact run commands for the two frontends.
```

## I2 — Deploy  🟣 Gemini Pro (config) + Claude Code (frontends)

```
Deploy Olrac Signage cheaply.
1. Supabase: production project already hosts Postgres + Auth + Storage. Run supabase/schema.sql there and
   create a public-read "media" Storage bucket.
2. Backend (FastAPI): deploy to Render or Railway (free/cheap tier). Provide a Dockerfile + start command
   (uvicorn app.main:app --host 0.0.0.0 --port $PORT) and the full env-var list to set.
3. Admin + TV (Vite builds): deploy each to Vercel or Netlify; set VITE_API_URL to the deployed backend URL
   and the Supabase vars on the admin.
4. TV on a real screen (recommended): build & sideload the **T5** Android-TV WebView kiosk wrapper APK — set
   its TV_URL to the deployed TV build, then set it as the Home app (or disable the stock launcher with
   `adb shell pm disable-user --user 0 com.google.android.tvlauncher`) for true kiosk + auto-start on boot.
   Zero-build fallback: open the deployed TV URL fullscreen in the Android TV browser.
Give complete configs + ordered steps for each.
```

---

## Quick reference

| Layer | Tool | Prompts | Status |
|-------|------|---------|--------|
| Backend (FastAPI + Supabase) | **opencode** — Gemini Pro for B1/B2/B4/B5, free models for B3/B6/B7 | B1–B7 | to build |
| Admin app (React+Vite) | **Claude Code** | A1–A7 | built in `admin/` (prompts = spec/regen/API-wire) |
| TV player (React+Vite kiosk) | **Claude Code** | T1–T4 (+ **T5** native kiosk wrapper) | web app built in `tv/`; T5 = optional Android-TV shell (from displayer's deployment model) |
| Integrate + deploy | Claude Code + Gemini Pro | I1–I2 | to do |

**Golden rules:** build in order; test after every prompt; never start a phase until the previous one runs
end-to-end. For opencode/free models: paste the Context Block every session, one file-group per prompt, demand
complete files, pin the contract. For Claude Code: point it at `@admin.html` / `@tv-player.html` and the
existing `admin/` & `tv/` code. **No purple — the accent is `#1E293B`.**
```
