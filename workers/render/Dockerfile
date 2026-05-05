FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Build context is the repo root (set in compose) so the worker's
# `portal-api` path dep can be satisfied. Layout in the image:
#   /app/apps/api       — sibling package referenced from pyproject.toml
#   /app/workers/render — the worker source itself
WORKDIR /app
COPY apps/api ./apps/api
COPY workers/render ./workers/render

# Pre-install apps/api so pip already knows about portal-api when it
# resolves the worker's deps. (uv's [tool.uv.sources] is a uv-only
# directive; pip ignores it and would otherwise look up portal-api on
# PyPI and fail.)
RUN pip install --no-cache-dir ./apps/api

WORKDIR /app/workers/render
RUN pip install --no-cache-dir .

CMD ["arq", "render.worker.WorkerSettings"]
