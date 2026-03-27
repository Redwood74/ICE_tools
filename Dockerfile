# ICEpicks Docker image
# Build:  docker build -t icepicks .
# Run:    docker run --env-file .env -v ./artifacts:/app/artifacts -v ./state:/app/state icepicks check-once

FROM python:3.12-slim AS base

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

# Default volumes for config, artifacts, state
VOLUME ["/app/artifacts", "/app/state"]

ENTRYPOINT ["findice"]
CMD ["check-once"]
