FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Local packages first (so dependency resolution picks our editable installs).
COPY workers/common/ /app/workers/common/
COPY apps/api/ /app/apps/api/
COPY supabase/ /app/supabase/
COPY prompts/ /app/prompts/

RUN pip install -e /app/workers/common \
 && pip install -e /app/apps/api

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
