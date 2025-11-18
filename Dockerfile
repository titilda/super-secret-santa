FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.6 /uv /uvx /bin/
COPY pyproject.toml uv.lock /app/
WORKDIR /app
RUN uv sync --frozen --no-cache --compile-bytecode --no-install-project && \
    mkdir -p /.cache/uv && \
    chown -R 99:100 /app /.cache/uv
COPY . /app/
USER 99:100

CMD ["uv", "run", "-m", "super_secret_santa"]