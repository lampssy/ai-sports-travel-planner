FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
COPY app ./app
RUN uv sync --no-dev --no-config

COPY README.md PROJECT.md LICENSE ./
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PATH="/app/.venv/bin:$PATH"
ENV APP_DB_PATH=/data/planner.db

CMD ["uv", "run", "--no-dev", "--no-config", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
