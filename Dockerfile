# ICEpicks Docker image
# Build:  docker build -t icepicks .
# Run:    docker run --env-file .env -v ./artifacts:/app/artifacts -v ./state:/app/state icepicks check-once

# Pin base image for reproducible builds. Update digest periodically.
# To find the latest digest: docker pull python:3.12-slim && docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
FROM python:3.12-slim@sha256:af4e85f1f34a6a7fa1092acb06e3cac03c11ccadea4e03b837b2e7e109520580 AS base

# Playwright system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdbus-1-3 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2 libatspi2.0-0 libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Install Playwright Chromium
RUN playwright install chromium

# Run as non-root user
RUN useradd -m -u 1000 findice && \
    chown -R findice:findice /app
USER findice

# Default volumes for config, artifacts, state
VOLUME ["/app/artifacts", "/app/state"]

ENTRYPOINT ["findice"]
CMD ["check-once"]
