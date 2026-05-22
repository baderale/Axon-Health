FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml README.md /app/
RUN pip install --upgrade pip \
    && pip install .

# Copy source.
COPY axon /app/axon
COPY seed_data /app/seed_data
COPY tests /app/tests

# Default command is the interceptor service; override for tools.
CMD ["python", "-m", "axon.gatekeeper.interceptor"]
