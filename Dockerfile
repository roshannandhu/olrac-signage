FROM python:3.11-slim

WORKDIR /app

# ffmpeg and libpq are required for media processing and postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir psycopg2-binary boto3 python-dotenv alembic

# Copy application source code
COPY backend/ ./backend/

EXPOSE 8000

# Dynamically bind to Render's $PORT (defaults to 8000)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
