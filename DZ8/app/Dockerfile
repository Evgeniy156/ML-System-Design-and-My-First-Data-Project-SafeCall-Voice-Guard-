FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app/
RUN mkdir -p /app/uploads /app/weights

EXPOSE 8080
CMD ["python", "api.py"]
