FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      libjpeg62-turbo zlib1g \
 && rm -rf /var/lib/apt/lists/*

COPY workers/common/     /app/workers/common/
COPY workers/image/      /app/workers/image/
COPY supabase/           /app/supabase/
COPY prompts/            /app/prompts/

RUN pip install -e /app/workers/common \
 && pip install -e /app/workers/image

CMD ["rq", "worker", "end_frame"]
