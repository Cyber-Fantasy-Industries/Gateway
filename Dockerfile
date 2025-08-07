FROM python:3.11

# Systemtools installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl procps lsof net-tools python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./

# Nur hier installieren!
RUN pip install --upgrade pip uv && uv sync

# Pfad auf das venv setzen (damit Kommandos wie "streamlit" im PATH landen)
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

COPY . .

EXPOSE 8000

