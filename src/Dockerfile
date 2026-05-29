FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}" \
    PORT=8088

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @playwright/cli@latest

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev

COPY dem333 ./dem333
COPY main.py server.py ./

EXPOSE 8088

CMD ["python", "server.py"]
