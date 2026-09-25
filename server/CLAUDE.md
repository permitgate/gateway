# Server instructions

These rules apply only to files and commands inside `server/`.

## Testing

- Always run server tests through `uv`.
- Use `uv run pytest`, never bare `pytest`.
- Use `uv run python ...`, never bare `python` or `python3`.
- Before finishing server changes, run:

```bash
PYTHONPATH=src uv run pytest tests