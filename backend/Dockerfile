FROM python:3.10-slim

WORKDIR /app

# ffmpeg is required by the media worker (P2 transcoding).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first so the layer caches across code changes.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir psycopg2-binary boto3 python-dotenv alembic

# Copy the backend as a PACKAGE under /app, not as loose modules.
#
# The build context is the project root on purpose. An earlier version used
# `context: ./backend` with `COPY . .`, which put main.py, models.py and routers/ directly
# in /app. `uvicorn main:app` then imported main as a top-level module and every
# `from . import database` failed with "attempted relative import with no known parent
# package" — the backend and worker containers both crash-looped on start.
COPY backend/ ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
