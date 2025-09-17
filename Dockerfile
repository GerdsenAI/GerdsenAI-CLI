# Runtime Dockerfile for GerdsenAI-CLI
# Uses PEP 517 build via pip to install project from pyproject.toml

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system deps minimally
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project
COPY pyproject.toml README.md ./
COPY gerdsenai_cli ./gerdsenai_cli

# Install project with runtime deps only
RUN pip install --upgrade pip setuptools wheel \
    && pip install .

# Default command: run the CLI
ENTRYPOINT ["gerdsenai"]
CMD ["--help"]
