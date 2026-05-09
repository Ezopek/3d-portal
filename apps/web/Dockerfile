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
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ARG SENTRY_URL
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN \
    VITE_PORTAL_VERSION=$VITE_PORTAL_VERSION \
    VITE_ENVIRONMENT=$VITE_ENVIRONMENT \
    VITE_GIT_COMMIT=$VITE_GIT_COMMIT \
    VITE_BUILD_TIME=$VITE_BUILD_TIME \
    SENTRY_ORG=$SENTRY_ORG \
    SENTRY_PROJECT=$SENTRY_PROJECT \
    SENTRY_URL=$SENTRY_URL

# SENTRY_AUTH_TOKEN is mounted by BuildKit at /run/secrets/sentry_token only
# during this RUN step; it never lands in any image layer (verifiable via
# `docker history`). The single-line env-var prefix exports the token into
# the npm child process and goes out of scope when that subprocess exits.
RUN --mount=type=secret,id=sentry_token \
    SENTRY_AUTH_TOKEN="$(cat /run/secrets/sentry_token)" \
    npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
