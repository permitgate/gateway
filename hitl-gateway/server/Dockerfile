FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY src/ /app/
COPY pyproject.toml /app
COPY uv.lock /app

WORKDIR /app

RUN ls -al
RUN uv sync --locked

CMD ["uv", "run", "main.py"]