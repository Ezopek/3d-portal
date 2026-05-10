FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Build context is the repo root (see infra/docker-compose.yml `api` and
# `arq-worker` services) so we can COPY both apps/api/* and docs/* into
# the runtime image. The repo-root context matches the worker service's
# pattern (workers/render/Dockerfile is built with the same context).

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir .

COPY apps/api/app ./app
COPY apps/api/alembic.ini ./
COPY apps/api/migrations ./migrations
COPY apps/api/scripts ./scripts

# Story 4.2 — self-serving agent runbook. Copied into a deterministic
# on-image path so the runbook version-locks with the API deploy.
# Read by `app.modules.runbook.router:get_runbook` and fingerprint-
# verified by `infra/scripts/deploy.sh` against `infra/.runbook-fingerprint`.
COPY docs/agents-add-model-runbook.md /app/static/agent-runbook.md

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
