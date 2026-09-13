FROM node:22-bookworm-slim AS node-dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts

FROM python:3.12-slim-bookworm AS application

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# SnarkJS runs in a small, isolated Node subprocess for each verification.
COPY --from=node-dependencies /usr/local/bin/node /usr/local/bin/node
COPY --from=node-dependencies /app/node_modules ./node_modules

COPY requirements.txt ./
RUN python -m pip install -r requirements.txt

COPY main.py verify.mjs ./
COPY zk ./zk

RUN useradd --create-home --uid 10001 qyvox \
    && chown -R qyvox:qyvox /app
USER qyvox

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
