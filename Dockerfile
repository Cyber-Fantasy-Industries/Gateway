FROM python:3.11-slim

WORKDIR /app

COPY . /app

ENV PYTHONPATH=/app

# --- Systemtools installieren ---
RUN apt-get update && \
    apt-get install -y curl procps lsof net-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt
