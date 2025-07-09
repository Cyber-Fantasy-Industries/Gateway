FROM python:3.11-slim

WORKDIR /app

COPY . /app

ENV PYTHONPATH=/app

COPY requirements.txt .
COPY web_dashboard/static /app/web_dashboard/static
COPY web_dashboard/templates /app/web_dashboard/templates

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

CMD ["python", "backend/main.py"]
