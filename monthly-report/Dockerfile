# OSP Monthly Report — Vite/React build + FastAPI runtime in one image.
# uvicorn serves dist/ (the SPA) and /api/*; data lives in the /data volume.

# ---------- stage 1: build the frontend ----------
FROM node:20-alpine AS web
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
# Sub-path the site is served under (e.g. /monthly) — baked into asset URLs.
ARG OSP_BASE_PATH=""
RUN OSP_BASE_PATH=$OSP_BASE_PATH npm run build

# ---------- stage 2: FastAPI runtime ----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Bangkok \
    OSP_STORAGE=/data
WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/__init__.py server/app.py server/etl.py server/companies.py server/
COPY --from=web /app/dist dist/

# Uploads land on this volume — run as an unprivileged user (uid 10001). The host
# folder mounted at /data must be owned by that uid.
RUN useradd --system --uid 10001 --home /app osp && mkdir -p /data && chown osp /data
USER osp
VOLUME ["/data"]
EXPOSE 8000
# Behind a proxy (cloudflared, Render): trust X-Forwarded-Proto so redirects stay https.
# PORT is set by hosts like Render; 8000 otherwise.
CMD uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips "*"
