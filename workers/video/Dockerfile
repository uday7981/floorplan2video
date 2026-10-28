FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY workers/common/     /app/workers/common/
COPY workers/video/      /app/workers/video/
COPY supabase/           /app/supabase/
COPY prompts/            /app/prompts/

RUN pip install -e /app/workers/common \
 && pip install -e /app/workers/video

CMD ["rq", "worker", "video"]
