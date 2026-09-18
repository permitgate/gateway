FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /uvx /bin/
WORKDIR /app

COPY server/pyproject.toml /app/
COPY server/uv.lock /app/
COPY server/alembic.ini /app/

RUN uv sync --locked

ENV PYTHONPATH=/app/src
COPY server/src /app/src/

WORKDIR /app/src

CMD ["uv", "run", "main.py"]