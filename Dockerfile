FROM python:3.13.7

ENV PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT="/usr/local/"

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
        gettext \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -Ls https://astral.sh/uv/install.sh | bash

COPY pyproject.toml uv.lock ./

RUN uv sync ; uv sync --frozen --no-cache --no-dev

COPY . .

RUN chmod +x /usr/src/app/entrypoint.sh
