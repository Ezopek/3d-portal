# syntax=docker/dockerfile:1
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --include=optional
COPY . .

ARG VITE_SENTRY_DSN
ARG VITE_PORTAL_VERSION
ARG VITE_ENVIRONMENT
ARG VITE_GIT_COMMIT
ARG VITE_BUILD_TIME
ARG VITE_BUILD_HOST
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ARG SENTRY_URL
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN \
    VITE_PORTAL_VERSION=$VITE_PORTAL_VERSION \
    VITE_ENVIRONMENT=$VITE_ENVIRONMENT \
    VITE_GIT_COMMIT=$VITE_GIT_COMMIT \
    VITE_BUILD_TIME=$VITE_BUILD_TIME \
    VITE_BUILD_HOST=$VITE_BUILD_HOST \
    SENTRY_ORG=$SENTRY_ORG \
    SENTRY_PROJECT=$SENTRY_PROJECT \
    SENTRY_URL=$SENTRY_URL

# SENTRY_AUTH_TOKEN is mounted by BuildKit at /run/secrets/sentry_token only
# during this RUN step; it never lands in any image layer (verifiable via
# `docker history`). The single-line env-var prefix exports the token into
# the npm child process and goes out of scope when that subprocess exits.
#
# `required=true` makes BuildKit fail the build if the secret source is
# missing — the host must export GLITCHTIP_AUTH_TOKEN before invoking
# `docker compose build`. The explicit non-empty guard then catches the
# "secret file present but empty" edge case so Sentry vite-plugin's
# warn-and-skip behavior does not silently produce a deploy without
# uploaded source maps (FR4 hard-fail policy).
RUN --mount=type=secret,id=sentry_token,required=true \
    sh -c 'SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)"; \
      if [ -z "$SENTRY_AUTH_TOKEN" ]; then \
        echo "✗ SENTRY_AUTH_TOKEN secret is empty (BuildKit mounted but file is blank)" >&2; \
        exit 1; \
      fi; \
      export SENTRY_AUTH_TOKEN; \
      npm run build'

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
