FROM python:3.11-slim

WORKDIR /app

COPY . /app

ENV PYTHONPATH=/app

COPY requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

CMD ["python", "backend/main.py"]
