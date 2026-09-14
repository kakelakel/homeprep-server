FROM node:22-alpine AS web-builder

RUN apk add --no-cache python3
WORKDIR /build
COPY scripts ./scripts
COPY web ./web
RUN python3 scripts/sync_brand_assets.py
WORKDIR /build/web
RUN npm install && npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOMEPREP_DATA_DIR=/data

WORKDIR /app

COPY pyproject.toml README.md LICENSE alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY --from=web-builder /build/web/dist ./web/dist

RUN pip install --no-cache-dir .

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8080

CMD ["sh", "-c", "alembic upgrade head && uvicorn homeprep_server.main:app --host 0.0.0.0 --port 8080"]
