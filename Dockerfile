FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install dependencies first for layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Install the project package
COPY src/ ./src/
RUN touch README.md
RUN uv sync --frozen --no-dev


FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
# Required for the editable src-layout install in .venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "simplefeed.server:app", "--host", "0.0.0.0", "--port", "8000"]
