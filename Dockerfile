FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY api-requirements.txt .
RUN pip install --no-cache-dir -r api-requirements.txt

COPY app/ ./app/
COPY data/ ./data/

ENV DB_PATH=/app/data/store.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
