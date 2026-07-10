# BoardWise web image (S20).
#
# Multi-stage build: `build` compiles the Vite/React bundle with Node; `final`
# serves the static bundle from nginx:alpine on :3006, proxying `/api` to the
# `api` compose service (see frontend/nginx.conf, decision §4.11).

FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:alpine AS final

RUN apk add --no-cache curl

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3006

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD curl -f http://localhost:3006/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
