FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ezdxf -> matplotlib needs system libs; keep minimal.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 libfreetype6 libxml2 \
 && rm -rf /var/lib/apt/lists/*

COPY workers/common/           /app/workers/common/
COPY packages/plan_schema/     /app/packages/plan_schema/
COPY workers/extract/          /app/workers/extract/
COPY supabase/                 /app/supabase/
COPY prompts/                  /app/prompts/

RUN pip install -e /app/workers/common \
 && pip install -e /app/packages/plan_schema \
 && pip install -e /app/workers/extract

# RQ worker loop consuming the "extract" queue.
CMD ["rq", "worker", "extract"]
