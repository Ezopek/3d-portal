FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --include=optional
COPY . .

ARG VITE_SENTRY_DSN
ARG VITE_PORTAL_VERSION
ARG VITE_ENVIRONMENT
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN \
    VITE_PORTAL_VERSION=$VITE_PORTAL_VERSION \
    VITE_ENVIRONMENT=$VITE_ENVIRONMENT

RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
