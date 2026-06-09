# Olrac Signage — Backend

FastAPI + Supabase backend for the Olrac cloud digital-signage platform.

## Prerequisites

- Python 3.11+
- A Supabase project (free tier works)
- A PUBLIC-READ Storage bucket named **`media`** in your Supabase project:
  1. Supabase Dashboard → Storage → New bucket
  2. Name: `media`, check "Public bucket"
  3. Click Create

## Setup

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your Supabase project credentials

# 4. Run the schema migration
# Paste the contents of supabase/schema.sql into Supabase → SQL Editor → Run

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```

## Verify

```bash
curl http://localhost:8000/health
# → {"data":{"status":"ok"},"error":null}
```

## Project structure

```
app/
  main.py              FastAPI app, CORS, router includes, health
  config.py            pydantic-settings from .env
  db.py                async SQLAlchemy engine (asyncpg)
  supabase_client.py   supabase-py client (service role)
  responses.py         envelope helpers + global exception handlers
  models.py            SQLAlchemy ORM classes
  schemas.py           Pydantic v2 request/response models
  routers/             Endpoint modules (created per prompt)
  services/            Business logic (playlist resolution, etc.)
  tasks.py             Background tasks (offline sweeper)
supabase/
  schema.sql           Idempotent Supabase SQL migration
scripts/
  seed_admin.py        Create the admin user
  smoke_test.py        End-to-end integration test
```

## API docs

Once the server is running, visit http://localhost:8000/docs for interactive Swagger UI.
