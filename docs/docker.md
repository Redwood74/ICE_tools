# Docker Deployment — ICEpicks

Run ICEpicks in a Docker container for isolated, reproducible execution
on any platform with Docker support.

> **Note:** Docker requires elevated privileges on most systems.
> If you cannot install Docker directly, consider a Linux VM
> (e.g. Hyper-V, WSL 2, or VirtualBox) and install Docker inside it.

---

## Quick start

```bash
# 1. Build the image
docker build -t icepicks .

# 2. Copy and configure .env
cp .env.example .env
# Edit .env with your A_NUMBER, COUNTRY, TEAMS_WEBHOOK_URL

# 3. Run a dry-run check
docker run --rm --env-file .env \
  -v ./artifacts:/app/artifacts \
  -v ./state:/app/state \
  icepicks check-once --dry-run

# 4. Run a real check
docker run --rm --env-file .env \
  -v ./artifacts:/app/artifacts \
  -v ./state:/app/state \
  icepicks check-once
```

---

## Using Docker Compose

```bash
# Build and run
docker compose run --rm findice check-once --dry-run

# Run batch mode (uncomment people.yml volume in docker-compose.yml)
docker compose run --rm findice check-batch --dry-run
```

---

## Batch mode (multi-person)

1. Create `people.yml` from the example:
   ```bash
   cp people.yml.example people.yml
   # Edit people.yml with real person entries
   ```

2. Uncomment the `people.yml` volume in `docker-compose.yml`:
   ```yaml
   volumes:
     - ./people.yml:/app/people.yml:ro
   ```

3. Set `PEOPLE_FILE=people.yml` in `.env`.

4. Run:
   ```bash
   docker compose run --rm findice check-batch --dry-run
   ```

---

## Scheduled execution inside Docker

### Option A: Host-based scheduling (recommended)

Use your host's scheduler (cron, Task Scheduler, launchd) to run
`docker run` at your desired interval:

```bash
# Example crontab entry (every 20 minutes)
*/20 * * * * docker run --rm --env-file /path/to/.env -v /path/to/artifacts:/app/artifacts -v /path/to/state:/app/state icepicks check-once >> /path/to/icepicks.log 2>&1
```

### Option B: In-container cron

Not recommended for this use case — the container should be ephemeral.
Use host-based scheduling instead.

---

## Volumes

| Mount point | Purpose | Required |
|---|---|---|
| `/app/artifacts` | Saved screenshots, HTML, text, reports | Yes |
| `/app/state` | Dedup state JSON | Yes |
| `/app/people.yml` | Multi-person config (read-only) | For batch mode |

> `.env` is passed via `--env-file`, not mounted as a volume, to avoid
> accidentally exposing secrets inside the container filesystem.

---

## Troubleshooting

### Browser fails to launch

Playwright needs specific system libraries. The Dockerfile installs them,
but if you're using a custom base image you may need to run:

```bash
playwright install-deps chromium
```

### Permission errors on volumes

Ensure the host directories exist and are writable:

```bash
mkdir -p artifacts state
```

### Container exits immediately

Check the exit code:
- `0` — success
- `1` — configuration error or all attempts failed
- `3` — bot challenge / CAPTCHA detected
