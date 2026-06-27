FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/root/.cache/huggingface

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

ENV HF_HUB_DISABLE_XET=1
ENV HF_HUB_DOWNLOAD_TIMEOUT=120
ENV HF_HUB_ETAG_TIMEOUT=30

COPY . /app/
RUN mkdir -p /app/uploads /app/weights /root/.cache/huggingface

CMD ["python", "main.py"]
