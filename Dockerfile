# Multi‑stage Dockerfile for GPUBROKER
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

FROM node:20-alpine AS nodebuilder
WORKDIR /frontend
COPY src/frontend/package*.json ./
RUN npm ci && npm run build

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app /app
COPY --from=nodebuilder /frontend/build ./frontend
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
