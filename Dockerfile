FROM python:3.11-slim

# Render / Docker — listens on $PORT (default 10000)
ENV PYTHONUNBUFFERED=True
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 120 "app:create_app()"
