FROM python:3.11

# Verhindert tzdata-Dialoge in CI / non-interactive
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Systemtools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata git curl jq \
    procps lsof iproute2 iputils-ping dnsutils netcat-openbsd net-tools \
    less nano \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies cachen: pyproject + (optional) uv.lock zuerst
COPY pyproject.toml uv.lock* ./

# Python-Umgebung via uv
RUN pip install --upgrade pip uv && uv sync --frozen || uv sync

RUN pip install --no-cache-dir pyflakes ruff
# Pfad setzen (damit z.B. uvicorn im PATH ist)
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

# Quellcode
COPY . .

# Uvicorn läuft (laut compose) auf 8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD curl -fsS http://localhost:8080/api/health || exit 1

# Optionaler Default-Start (Compose kann das überschreiben)
CMD [ "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080" ]