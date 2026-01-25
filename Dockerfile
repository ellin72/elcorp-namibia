FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

# OS deps for common Python packages and Postgres client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# Copy app
COPY . /app

# Create logs dir expected by app
RUN mkdir -p /app/logs

ENV FLASK_APP=run.py \
    FLASK_ENV=production

EXPOSE 5000

# Production server
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5000", "--workers", "3", "--log-level", "info"]