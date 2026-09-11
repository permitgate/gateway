FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml /app/
COPY uv.lock /app/
COPY src/ /app/src/

RUN uv sync --locked

ENV PYTHONPATH=/app/src

WORKDIR /app/src

CMD ["uv", "run", "main.py"]