# backend/Dockerfile
#
# Builds the FastAPI backend into a Docker image.
#
# Why single-stage (not multi-stage)?
#   Multi-stage builds copy a virtual environment from a builder container
#   into a runtime container. The problem: Python script shebang lines contain
#   the original builder path (e.g. #!/build/.venv/bin/python3) which does not
#   exist in the runtime container — causing "no such file or directory" crashes.
#   Installing directly into the system Python avoids this entirely.
#
# Local development: use Poetry (`poetry install`, `poetry run pytest`).
# Docker production: use pip + requirements.txt (simpler, no relocation issues).

FROM python:3.11-slim

# Create a non-root system user for security.
# Containers running as root are a security risk — if the app is compromised,
# the attacker would have root access to the container file system.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy requirements.txt first, BEFORE copying application code.
# Why? Docker caches each instruction as a layer. If requirements.txt hasn't
# changed, Docker reuses the cached pip install layer — much faster rebuilds.
COPY requirements.txt ./

# Install dependencies into the system Python.
# --no-cache-dir: don't store pip's download cache in the image (saves space).
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application source code AFTER pip install.
# This way, changing a .py file only re-runs this COPY step, not pip install.
COPY app/ ./app/

# PYTHONUNBUFFERED=1: print() and logging output appears in docker logs immediately.
# Without this, Python buffers output and you might miss log lines on crashes.
ENV PYTHONUNBUFFERED=1

# Switch to non-root user before running the app.
USER appuser

EXPOSE 8000

# Use `python -m uvicorn` (module mode) rather than the `uvicorn` script.
# The module mode invokes Python directly, bypassing any shebang path issues.
# --host 0.0.0.0: listen on all network interfaces inside the container.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
